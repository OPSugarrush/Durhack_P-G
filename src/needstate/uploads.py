"""Session uploads: conversion stays separate from collection analysis."""
import hashlib
import secrets

import pandas as pd

from needstate.workspace import workbook, to_canonical, combine, analyse_lines
from needstate.pipeline import process_lines


def describe(lines):
    return dict(receipts=int(lines.transaction_id.nunique()), items=len(lines),
                shoppers=int(lines.customer_id.nunique()),
                start=str(lines.timestamp.min().date()), end=str(lines.timestamp.max().date()))


def build_report(lines, cfg, progress):
    if lines.transaction_id.nunique() != 1:
        return analyse_lines(lines, cfg, progress=progress)
    resolved = process_lines(lines, cfg).lines
    items = []
    for row in resolved.to_dict('records'):
        value = row['line_total']
        category = str(row['category']).replace('_', ' ')
        if category == 'unclassified':
            category = 'category not yet identified'
        items.append(dict(product=row['raw_product_text'], category=category,
                          amount=float(value) if pd.notna(value) else None))
    known = [i['amount'] for i in items if i['amount'] is not None]
    return dict(total=1, buyers=int(lines.customer_id.nunique()), findings=[], spending=[],
                receipt_summary=dict(describe(lines), items=items,
                                     known_spend=sum(known) if known else None, priced=len(known)))


def stage(data, filename, kind, cfg, ocr_cache=None):
    batch = dict(id=secrets.token_hex(12), filename=filename, kind=kind,
                 digest=hashlib.sha256(data).hexdigest(), accepted=False, revision=0)
    if kind == 'spreadsheet':
        batch['lines'], batch['skipped'] = workbook(data, cfg.mapping)
    elif kind == 'photo':
        try:
            from needstate_receipt_ingestion.images import prepare_images
            from needstate_receipt_ingestion.extraction import extract_receipt
            from needstate_receipt_ingestion.export import new_id
        except ImportError as exc:
            raise ValueError('Receipt reading is not installed. Install the project with its ocr extra.') from exc
        cache_key = (batch['digest'], filename.rsplit('.', 1)[-1].lower())
        cached = ocr_cache.get(cache_key) if ocr_cache is not None else None
        if cached is None:
            pages = prepare_images(data, filename)
            original = extract_receipt(pages)
            if ocr_cache is not None:
                # Session-local and bounded: no cross-user or permanent image cache.
                if len(ocr_cache) >= 2:
                    ocr_cache.pop(next(iter(ocr_cache)))
                ocr_cache[cache_key] = (pages, original)
        else:
            pages, original = cached
        batch['pages'] = list(pages)
        batch['original'] = original.model_copy(deep=True)
        batch['receipt'] = batch['original']
        batch['receipt_id'] = new_id('R')
        batch['consumer'] = new_id('C')
    else:
        raise ValueError('Choose a spreadsheet or receipt photo.')
    return batch


def review(batch):
    result = {k: batch[k] for k in ('id', 'filename', 'kind', 'accepted', 'revision')}
    result['currency'] = batch.get('currency')
    result['export_ready'] = batch['kind'] == 'photo' and 'lines' in batch
    if batch['kind'] == 'photo':
        from needstate_receipt_ingestion.validation import check_receipt
        result.update(receipt=batch['receipt'].model_dump(mode='json'),
                      consumer=batch['consumer'], pages=len(batch['pages']), issues=check_receipt(batch['receipt']))
    else:
        result['summary'] = describe(batch['lines'])
    return result


def save_review(batch, payload):
    from needstate_receipt_ingestion.models import Receipt
    if batch['kind'] != 'photo' or batch['accepted']:
        raise ValueError('Only an uncommitted photo review can be edited.')
    if payload.get('revision') != batch['revision']:
        raise ValueError('This review changed in another window. Reopen Import before editing.')
    receipt = Receipt.model_validate(payload['receipt'])
    batch.update(receipt=receipt, consumer=str(payload.get('consumer', '')).strip(),
                 revision=batch['revision'] + 1)
    batch.pop('lines', None)
    batch.pop('analysis_cache', None)


def prepare_commit(batch, payload, cfg):
    if batch['kind'] == 'spreadsheet':
        return batch['lines']
    if batch['accepted']:
        return batch['lines']
    from needstate_receipt_ingestion.models import Receipt
    from needstate_receipt_ingestion.export import dataframe
    receipt = Receipt.model_validate(payload['receipt'])
    if payload.get('revision') != batch['revision']:
        raise ValueError('This review changed. Reopen Import before continuing.')
    consumer = str(payload.get('consumer', '')).strip()
    if receipt != batch['receipt'] or consumer != batch['consumer']:
        raise ValueError('Save your changes and refresh the receipt checks before continuing.')
    if not consumer:
        raise ValueError('Choose a pseudonymous shopper ID for this receipt.')
    if not receipt.date:
        raise ValueError('Confirm the receipt date before analysing it.')
    products = [e for e in receipt.entries if e.kind == 'product']
    if not products or any(not (e.description or '').strip() for e in products):
        raise ValueError('Each purchased item needs a product description.')
    if not payload.get('reviewed'):
        raise ValueError('Review the extracted items before continuing.')
    frame = dataframe(receipt, consumer, batch['receipt_id'], batch['filename'])
    lines = to_canonical(frame, cfg.mapping)
    # A zero adjustment is not evidence of a promotion; a missing one is unknown.
    lines['promotion_flag'] = pd.array(
        [True if pd.notna(v) and v < 0 else pd.NA for v in frame['Promotion']], dtype='boolean')
    batch.update(receipt=receipt, consumer=consumer, lines=lines)
    return lines


def possible_duplicates(old, new):
    """Flag same-day matching baskets without assuming identical receipt IDs."""
    if old is None:
        return []
    def signatures(frame):
        result = {}
        for tid, rows in frame.groupby('transaction_id'):
            first = rows.iloc[0]
            products = tuple(sorted((str(r.raw_product_text).strip().casefold(),
                                     '' if pd.isna(r.line_total) else str(float(r.line_total)))
                                    for r in rows.itertuples()))
            key = (str(first.timestamp.date()), products)
            result.setdefault(key, []).append(str(tid))
        return result
    existing = signatures(old)
    return [tid for key, ids in signatures(new).items() if key in existing
            for tid in ids if tid not in existing[key]]
