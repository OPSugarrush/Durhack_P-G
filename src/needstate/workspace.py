"""Receipt workspace: validate imports atomically and trace every finding to receipts."""
from collections import defaultdict
from io import BytesIO
import numpy as np
from scipy.stats import binomtest
from needstate.patterns.stats import benjamini_hochberg
from zipfile import BadZipFile, ZipFile

import pandas as pd
from openpyxl import load_workbook

from needstate.config import ROOT, load_config
from needstate.ingestion.adapters import to_canonical
from needstate.need_state.inference import predict_basket
from needstate.need_state.observations import replicated_pairs, group_status
from needstate.pipeline import process_lines


def config():
    local = ROOT / "configs/pipeline.local.yaml"
    return load_config(local if local.exists() else ROOT / "configs/pipeline.yaml")


def workbook(data, mapping):
    try:
        with ZipFile(BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 128 * 1024**2:
                raise ValueError("Workbook is too large after expansion. Split it into smaller files.")
        book = load_workbook(BytesIO(data), read_only=True, data_only=True)
        try:
            fields = mapping["fields"]
            required = {fields[k] for k in ("transaction_id", "raw_product_text")} | {fields.get("timestamp", fields.get("date"))}
            matches = []
            for sheet in book:
                rows = sheet.values
                header = [str(v).strip() for v in next(rows, ())]
                if required <= set(header):
                    matches.append((sheet, header))
            preferred = [m for m in matches if m[0].title == mapping["source"].get("sheet")]
            selected = preferred or matches
            if len(selected) != 1:
                raise ValueError("Use one receipt sheet with these headers: " + ", ".join(sorted(required)))
            sheet, header = selected[0]
            if any(header.count(v) > 1 for v in fields.values()):
                raise ValueError("The receipt sheet contains duplicate column headings.")
            df = pd.DataFrame(sheet.values)
            if len(df) < 2:
                raise ValueError("The receipt sheet has no purchase lines.")
            df = df.iloc[1:].set_axis(header, axis=1).dropna(how="all")
        finally:
            book.close()
    except (BadZipFile, KeyError, OSError) as exc:
        raise ValueError("Choose a readable, unencrypted .xlsx workbook.") from exc
    for key in ("transaction_id", "customer_id"):
        col = fields.get(key)
        if col in df:
            df[col] = df[col].astype("string").str.strip().replace("", pd.NA)
    explicit = fields.get("line_number") in df and df[fields["line_number"]].notna().all()
    if fields.get("line_number") in df and df[fields["line_number"]].notna().any() and not explicit:
        raise ValueError("Some line numbers are blank. Fill them in or remove the column.")
    lines = to_canonical(df, mapping)
    for field in ("Pack Size", "Format", "Ingredients", "Customer Feedback"):
        if field in df:
            lines[field] = df[field].reset_index(drop=True).astype("string")
    skipped = 0
    if explicit:
        before = len(lines)
        lines = lines.drop_duplicates()
        skipped = before - len(lines)
        if lines.duplicated(["transaction_id", "line_number"]).any():
            raise ValueError("Conflicting items share a receipt and line number. Nothing was imported.")
    return lines.reset_index(drop=True), skipped


def combine(old, new):
    if old is None:
        return new, 0
    common = set(old.transaction_id) & set(new.transaction_id)
    if common:
        def signatures(frame):
            cols = sorted((set(old) | set(new)) - {"line_id"})
            sub = frame[frame.transaction_id.isin(common)]
            return {tid: sorted(map(tuple, g.reindex(columns=cols).astype("string").fillna("").values.tolist()))
                    for tid, g in sub.groupby("transaction_id")}
        a, b = signatures(old), signatures(new)
        for tid in sorted(common):
            if a[tid] != b[tid]:
                raise ValueError(f"Receipt {tid} overlaps with different lines. Check both workbooks; nothing was imported.")
    return pd.concat([old, new[~new.transaction_id.isin(common)]], ignore_index=True), len(common)


def behaviour(a, b, n, m):
    if min(n, m) < 2:
        return "Limited history"
    if not a: return "Newly observed"
    if not b: return "No recent purchase"
    change = b / m - a / n
    if change >= .25: return "More frequent"
    if change <= -.25: return "Less frequent"
    if min(a, b) >= 2 and min(a/n, b/m) >= .5: return "Established routine"
    return "Occasional purchase"


def analyse_lines(lines, cfg):
    pl = process_lines(lines, cfg)
    profiles = pl.hierarchy.set_index("family_id").to_dict("index")
    conf = pl.resolution.catalogue.set_index("family_id").confidence.to_dict()
    quality = pl.quality.data_completeness.to_dict()
    cutoff = cfg.need_states["thresholds"]["abstain_below_score"]
    receipts, findings, trips, history = {}, defaultdict(dict), defaultdict(list), defaultdict(list)
    held = 0
    replicated, variable = replicated_pairs(pl.lines)
    for tid, g in pl.lines.groupby("transaction_id", sort=False):
        families = list(g.family_id.dropna().unique())
        prices = dict(zip(g.family_id, g.unit_price))
        attributes = defaultdict(dict)
        for field in ("Pack Size", "Format", "Ingredients", "Customer Feedback"):
            if field in g:
                for family, value in zip(g.family_id,g[field]):
                    if pd.notna(value):
                        attributes[family].setdefault(field, set()).add(str(value))
        pred = predict_basket(tid, families, pl.hierarchy, cfg.need_states, quality[tid], conf, profiles=profiles, replicated=replicated)
        customer = g.customer_id.dropna()
        buyer = str(customer.iloc[0]) if len(customer) else None
        day = g.timestamp.iloc[0].date().isoformat()
        labels = set()
        parts = []
        for part in pred.mission_partitions:
            candidates = [c for c in pred.candidate_needs if c["partition_id"] == part["partition_id"] and c["score"] >= cutoff]
            if not pred.abstained:
                labels.update(c["label"] for c in candidates)
            parts.append(dict(products=[profiles[f]["family_name"] for f in part["product_ids"]],
                              basis=group_status(part["product_ids"], replicated, variable),
                              prices=[float(prices[f]) if pd.notna(prices[f]) and np.isfinite(prices[f]) else None for f in part["product_ids"]],
                              attributes=[{k:sorted(v) for k,v in attributes[f].items()} for f in part["product_ids"]],
                              categories=[profiles[f]["category"].replace("_"," ").capitalize() for f in part["product_ids"]],
                              ambiguous=[profiles[f]["family_name"] for f in part["ambiguous_product_ids"]],
                              needs=[dict(label=c["label"], score=c["score"], support=[profiles[f]["family_name"] for f in c["supporting_product_ids"]]) for c in candidates]))
        receipts[tid] = dict(id=tid, buyer=buyer, date=day, parts=parts, abstained=pred.abstained,
                             quality=pred.data_completeness, confidence=pred.model_confidence, margin=pred.evidence_concentration)
        held += pred.abstained
        if buyer is not None:
            trips[buyer].append((day,tid))
        for label in labels:
            findings[("Shopping mission", label)].setdefault(buyer, []).append(tid)
        if len(labels) > 1:
            findings[("Mixed basket", "Several needs in one shop")].setdefault(buyer, []).append(tid)
        if buyer is not None:
            for cat in set(g.category.dropna()) - {"unclassified"}:
                history[buyer,cat].append((day,tid))
    dates = pd.to_datetime(lines.timestamp).dt.normalize()
    split = dates.min() + pd.Timedelta(days=((dates.max()-dates.min()).days+1)//2)
    boundary = split.date().isoformat()
    totals = {k:(sum(d < boundary for d,_ in v),sum(d >= boundary for d,_ in v)) for k,v in trips.items()}
    counts = {}
    for (buyer,cat), items in history.items():
        a = sum(d < boundary for d,_ in items)
        b = len(items)-a
        n,m = totals[buyer]
        key = behaviour(a,b,n,m), cat.replace("_"," ").capitalize()
        findings[key][buyer] = [tid for _,tid in items]
        counts[key,buyer] = [a,n,b,m]
    # Test categories across all comparable buyers, never the selected directional subgroup.
    eligible = [k for k,(n,m) in totals.items() if min(n,m) >= 2]
    category_evidence = {}
    pvalues = []
    rng = np.random.default_rng(42)
    for cat in sorted({cat for _,cat in history}):
        if len(eligible) < 5:
            break
        delta = []
        for buyer in eligible:
            items = history.get((buyer,cat), [])
            n,m = totals[buyer]
            early = sum(d < boundary for d,_ in items)
            delta.append(100*((len(items)-early)/m - early/n))
        delta = np.array(delta)
        pos,neg = int((delta>0).sum()), int((delta<0).sum())
        pvalues.append(binomtest(pos,pos+neg).pvalue if pos+neg else 1.)
        bootstrap = [rng.choice(delta, size=len(delta)).mean() for _ in range(500)]
        lo,hi = np.quantile(bootstrap,[.025,.975])
        category_evidence[cat.replace("_"," ").capitalize()] = dict(
            buyers=len(delta), change=round(float(delta.mean()),1),
            low=round(float(lo),1), high=round(float(hi),1))
    for ev,q in zip(category_evidence.values(),benjamini_hochberg(np.array(pvalues))):
        ev["q"] = round(float(q),5)
    result = []
    for (kind,label), by_buyer in sorted(findings.items(), key=lambda item: -sum(map(len,item[1].values()))):
        inference = ""
        matches = [tid for tids in by_buyer.values() for tid in tids]
        if kind == "Shopping mission":
            corroborated = sum(any(part["basis"] == "All pairs repeated across both periods"
                and any(need["label"] == label for need in part["needs"])
                for part in receipts[tid]["parts"]) for tid in matches)
            support = defaultdict(int)
            for tid in matches:
                names = {name for part in receipts[tid]["parts"] for need in part["needs"]
                         if need["label"] == label for name in need["support"]}
                for name in names:
                    support[name] += 1
            product = min(support, key=lambda name: (-support[name], name))
            inference = (f"Products used for {label.lower()} appeared on {len(matches)} trips. "
                         f"{product} was the most frequent example, bought on {support[product]} of those trips.")
            if corroborated:
                inference += f" On {corroborated} trips, the supporting group also contained pairings that repeated above expectation before and after {boundary}."
        elif kind == "Mixed basket":
            inference = f"On {len(matches)} trips, the products suggest more than one purpose for the same shop."
        elif kind in ("More frequent","Less frequent","No recent purchase","Newly observed"):
            comparisons = np.array([counts[((kind,label),buyer)] for buyer in by_buyer])
            early = np.mean(comparisons[:,0]/comparisons[:,1])
            late = np.mean(comparisons[:,2]/comparisons[:,3])
            inference = (f"For these {len(by_buyer)} buyers, {label.lower()} appeared on an average "
                         f"of {early:.0%} of earlier trips and {late:.0%} of trips from {boundary}.")
        result.append(dict(kind=kind,label=label,inference=inference,customers=[
            dict(id=k, receipts=v, counts=counts.get(((kind,label),k))) for k,v in by_buyer.items()],
            buyers=sum(k is not None for k in by_buyer), baskets=sum(map(len,by_buyer.values()))))
    return dict(receipts=receipts, findings=result, replicated_pairs=len(replicated), category_evidence=category_evidence, buyers=len(trips), total=len(receipts), held=held,
                start=dates.min().date().isoformat(), end=dates.max().date().isoformat(), split=boundary,
                variants=len(pl.resolution.variant_map), families=len(profiles), review=len(pl.resolution.review_pairs))
