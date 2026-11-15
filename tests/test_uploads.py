import pytest
from needstate.webapp import Store
from needstate.uploads import stage, build_report
from needstate.workspace import config
from tests.test_workspace import encoded, ROW


def test_focus_append_retry_and_conflict():
    s = Store()
    s.upload(encoded([ROW]), 'first.xlsx', 'spreadsheet')
    first = dict(batch_id=s.batch['id'], mode='append')
    s.commit(first)
    assert len(s.collection) == 1
    original = s.collection_report
    s.commit(first)
    assert len(s.collection) == 1
    other = ROW.copy()
    other[0] = '002'
    other[2] = '2026-04-02'
    s.upload(encoded([other]), 'second.xlsx', 'spreadsheet')
    s.commit(dict(batch_id=s.batch['id'], mode='focus'))
    assert len(s.collection) == 1 and s.collection_report is original
    assert s.lines.transaction_id.iloc[0] == '002'
    s.commit(dict(batch_id=s.batch['id'], mode='append'))
    assert s.collection.transaction_id.nunique() == 2
    saved = s.collection
    other[3] = 'CONFLICT'
    s.upload(encoded([other]), 'conflict.xlsx', 'spreadsheet')
    with pytest.raises(ValueError, match='overlaps'):
        s.commit(dict(batch_id=s.batch['id'], mode='append'))
    assert s.collection is saved
    assert s.collection_report['spending_unavailable']


def test_single_receipt_missing_spend_is_not_zero():
    row = ROW.copy()
    row[-1] = None
    cfg = config()
    batch = stage(encoded([row]), 'one.xlsx', 'spreadsheet', cfg)
    result = build_report(batch['lines'], cfg, lambda _: None)
    assert result['receipt_summary']['known_spend'] is None
    assert result['findings'] == []


def test_photo_review_revision_and_saved_content():
    pytest.importorskip('pydantic')
    from pathlib import Path
    from needstate_receipt_ingestion.models import Receipt
    from needstate.uploads import save_review, prepare_commit
    receipt = Receipt.model_validate_json(Path('receipt_ingestion/examples/receipt.json').read_text())
    batch = dict(kind='photo', accepted=False, revision=0, receipt=receipt,
                 consumer='shopper', receipt_id='photo-1', filename='photo.png')
    payload = dict(receipt=receipt.model_dump(mode='json'), consumer='shopper',
                   revision=0, reviewed=True)
    payload['receipt']['store_name'] = 'Corrected store'
    with pytest.raises(ValueError, match='Save your changes'):
        prepare_commit(batch, payload, config())
    save_review(batch, payload)
    with pytest.raises(ValueError, match='review changed'):
        prepare_commit(batch, payload, config())
    payload['revision'] = 1
    lines = prepare_commit(batch, payload, config())
    assert lines.transaction_id.nunique() == 1
    assert batch['receipt'].store_name == 'Corrected store'


def test_possible_duplicates_require_different_receipt_identity():
    from needstate.uploads import possible_duplicates
    from needstate.workspace import workbook
    original, _ = workbook(encoded([ROW]), config().mapping)
    assert possible_duplicates(original, original) == []
    other = original.copy()
    other['transaction_id'] = 'different-id'
    assert possible_duplicates(original, other) == ['different-id']


def test_declared_currency_enables_spending_for_collection():
    s = Store()
    s.upload(encoded([ROW]), 'gbp.xlsx', 'spreadsheet')
    s.commit(dict(batch_id=s.batch['id'], mode='append', currency='GBP'))
    assert s.report['currency'] == 'GBP'
    assert 'spending_unavailable' not in s.report
    other = ROW.copy()
    other[0], other[2] = 'second', '2026-04-02'
    s.upload(encoded([other]), 'eur.xlsx', 'spreadsheet')
    s.commit(dict(batch_id=s.batch['id'], mode='append', currency='EUR'))
    assert s.report['spending_unavailable']
    assert s.collection.transaction_id.nunique() == 2


def test_reviewed_photo_download_uses_teammate_workbook_contract():
    pytest.importorskip('pydantic')
    import threading
    from pathlib import Path
    from io import BytesIO
    from urllib.request import urlopen
    from openpyxl import load_workbook
    from needstate_receipt_ingestion.models import Receipt
    from needstate_receipt_ingestion.export import COLUMNS
    from needstate.webapp import server
    from needstate.uploads import prepare_commit, save_review
    receipt = Receipt.model_validate_json(Path('receipt_ingestion/examples/receipt.json').read_text())
    batch = dict(id='review-id', kind='photo', accepted=False, revision=0, receipt=receipt,
                 consumer='shopper', receipt_id='photo-1', filename='photo.png')
    payload = dict(receipt=receipt.model_dump(mode='json'), consumer='shopper', revision=0, reviewed=True)
    prepare_commit(batch, payload, config())
    http = server(0)
    http.store.batch = batch
    threading.Thread(target=http.serve_forever, daemon=True).start()
    try:
        with urlopen(f'http://127.0.0.1:{http.server_port}/api/export?batch=review-id') as response:
            book = load_workbook(BytesIO(response.read()), read_only=True)
            assert list(next(book.active.values)) == COLUMNS
            assert book.active.max_row > 1
            book.close()
        batch['analysis_cache'] = ('old revision', {'old': 'report'})
        save_review(batch, payload)
        assert 'analysis_cache' not in batch
        assert 'lines' not in batch  # Changed draft is not an approved export.
    finally:
        http.shutdown()
        http.server_close()


def test_large_preview_is_complete_and_bound_to_batch():
    import base64
    import random
    import threading
    from io import BytesIO
    from urllib.request import urlopen
    from urllib.error import HTTPError
    from PIL import Image
    from needstate.webapp import server
    raw = BytesIO()
    Image.frombytes('RGB', (512, 512), random.Random(12).randbytes(512*512*3)).save(raw, format='JPEG')
    encoded_image = raw.getvalue()
    assert len(encoded_image) > 65536
    http = server(0)
    http.store.batch = dict(id='current', kind='photo', pages=['data:image/jpeg;base64,'+base64.b64encode(encoded_image).decode()])
    threading.Thread(target=http.serve_forever, daemon=True).start()
    try:
        base = f'http://127.0.0.1:{http.server_port}/api/preview?batch='
        with urlopen(base+'current', timeout=10) as response:
            assert response.read() == encoded_image
        with pytest.raises(HTTPError) as error:
            urlopen(base+'previous', timeout=10)
        assert error.value.code == 404
    finally:
        http.shutdown()
        http.server_close()


def test_completed_scope_is_reused_without_reanalysis(monkeypatch):
    import needstate.webapp as webapp
    original = webapp.build_report
    calls = []
    def measured(*args):
        calls.append(True)
        return original(*args)
    monkeypatch.setattr(webapp, 'build_report', measured)
    s = Store()
    data = encoded([ROW])
    s.upload(data, 'one.xlsx', 'spreadsheet')
    command = dict(batch_id=s.batch['id'], mode='focus', currency='GBP')
    s.commit(command)
    first = s.report['receipt_summary']
    s.commit(command)
    s.commit(dict(command, mode='append'))
    s.upload(data, 'same.xlsx', 'spreadsheet')
    s.commit(dict(batch_id=s.batch['id'], mode='append', currency='GBP'))
    assert len(calls) == 1
    assert s.report['receipt_summary'] == first
    assert 'analysis_cache' not in next(iter(s.sources.values()))
    assert 'lines' not in next(iter(s.sources.values()))


def test_ocr_cache_preserves_original_and_generates_new_receipt_ids(monkeypatch):
    pytest.importorskip('pydantic')
    from pathlib import Path
    from needstate_receipt_ingestion.models import Receipt
    import needstate_receipt_ingestion.extraction as extraction
    fixture = Receipt.model_validate_json(Path('receipt_ingestion/examples/receipt.json').read_text())
    calls = []
    def extract(_):
        calls.append(True)
        return fixture
    monkeypatch.setattr(extraction, 'extract_receipt', extract)
    raw = Path('receipt_ingestion/examples/demo_receipt.png').read_bytes()
    cache = {}
    first = stage(raw, 'first.png', 'photo', config(), cache)
    first['receipt'].store_name = 'Manual correction'
    second = stage(raw, 'second.png', 'photo', config(), cache)
    assert len(calls) == 1
    assert second['receipt'].store_name == fixture.store_name
    assert first['receipt_id'] != second['receipt_id']
