"""Degradation metrics: how much do product matching, pair structure and need-states move under corruption?"""
from __future__ import annotations

import numpy as np
import pandas as pd

from needstate.baskets.construction import build_basket_matrix
from needstate.config import Config
from needstate.missing_data.simulation import MECHANISM, corrupt_lines
from needstate.need_state.inference import predict_all
from needstate.patterns.cooccurrence import null_model_pairs
from needstate.patterns.trends import trend_scan
from needstate.pipeline import PipelineResult, process_lines

CANON_COLS = [
    "line_id", "transaction_id", "customer_id", "retailer_id", "store_id", "timestamp", "raw_product_text",
    "quantity", "unit_price", "line_total", "promotion_label", "promotion_flag", "line_number", "receipt_total", "image_ref",
]


def _top_pairs(res: PipelineResult, truth_of_family: dict[str, str] | None, k: int = 30) -> set[tuple[str, str]]:
    bm = build_basket_matrix(res.lines, "family")
    pr = null_model_pairs(bm, n_perm=49, min_count=5).sort_values("adj_lift", ascending=False).head(k)
    out = set()
    for a, b in zip(pr["family_a"], pr["family_b"]):
        if truth_of_family:
            a, b = truth_of_family.get(a, a), truth_of_family.get(b, b)
        out.add(tuple(sorted((a, b))))
    return out


def evaluate_corruption(
    clean: PipelineResult,
    config: Config,
    kind: str,
    level: float,
    seed: int = 0,
    sample_receipts: int = 400,
    clean_pred: pd.DataFrame | None = None,
    clean_pairs: set | None = None,
) -> dict:
    base = clean.lines[CANON_COLS + ["category"]]
    bad = corrupt_lines(base, kind, level, seed)
    res = process_lines(bad[CANON_COLS], config)

    # --- product matching: purity (false merges) and fragmentation (splits) vs the clean mapping
    truth = clean.lines.drop_duplicates("line_id").set_index("line_id")["family_id"]
    lines = res.lines.copy()
    lines["_orig"] = lines["line_id"].astype(str).str.replace("-dup", "", regex=False)
    lines["truth"] = lines["_orig"].map(truth)
    ok = lines.dropna(subset=["family_id", "truth"])
    maj = ok.groupby("family_id")["truth"].agg(lambda s: s.value_counts().idxmax())
    purity = float((ok["truth"] == ok["family_id"].map(maj)).mean()) if len(ok) else np.nan
    maj_t = ok.groupby("truth")["family_id"].agg(lambda s: s.value_counts().idxmax())
    frag = float((ok["family_id"] == ok["truth"].map(maj_t)).mean()) if len(ok) else np.nan
    to_truth = maj.to_dict()

    # --- co-purchase structure stability (top-30 consumer-adjusted pairs, in truth space)
    cp = clean_pairs if clean_pairs is not None else _top_pairs(clean, None)
    bp = _top_pairs(res, to_truth)
    jacc = len(cp & bp) / max(len(cp | bp), 1)

    # --- need-state degradation on a fixed receipt sample
    cp_df = clean_pred
    if cp_df is None:
        rng = np.random.default_rng(1)
        tids = set(rng.choice(clean.lines["transaction_id"].unique(), size=min(sample_receipts, clean.lines["transaction_id"].nunique()), replace=False))
        cp_df = predict_all(clean.lines, clean.hierarchy, config.need_states, clean.quality, transaction_ids=tids)
    bp_df = predict_all(res.lines, res.hierarchy, config.need_states, res.quality, transaction_ids=set(cp_df["transaction_id"]))
    m = cp_df.merge(bp_df, on="transaction_id", suffixes=("_clean", "_bad"))
    bad_top = m["top_need_bad"].where(m["top_need_bad"].isin(set(cp_df["top_need"])) | m["top_need_bad"].isna(), m["top_need_bad"])
    agree = float((m["top_need_clean"] == bad_top).mean()) if len(m) else np.nan
    # --- trends: false alarms induced by the corruption itself
    trends = trend_scan(build_basket_matrix(res.lines, "family"))
    return {
        "kind": kind,
        "mechanism": MECHANISM[kind],
        "level": level,
        "families_found": int(len(res.resolution.catalogue)),
        "match_purity": purity,
        "match_completeness": frag,
        "pair_top30_jaccard": jacc,
        "need_top1_agreement": agree,
        "abstention_rate": float(bp_df["abstained"].mean()) if len(bp_df) else np.nan,
        "abstention_rate_clean": float(cp_df["abstained"].mean()),
        "mean_model_confidence_shift": float(bp_df["model_confidence"].mean() - cp_df["model_confidence"].mean()) if len(bp_df) else np.nan,
        "receipts_remaining_share": float(res.lines["transaction_id"].nunique() / clean.lines["transaction_id"].nunique()),
        "lines_remaining_share": float(len(bad) / len(base)),
        "trend_flags_after_corruption": int(trends["significant"].sum()),
    }


def run_experiment(
    clean: PipelineResult,
    config: Config,
    kinds: list[str] | None = None,
    levels: tuple[float, ...] = (0.05, 0.10, 0.20, 0.30),
    seed: int = 0,
    sample_receipts: int = 400,
    progress=None,
) -> pd.DataFrame:
    kinds = kinds or list(MECHANISM)
    rng = np.random.default_rng(1)
    tids = set(rng.choice(clean.lines["transaction_id"].unique(), size=min(sample_receipts, clean.lines["transaction_id"].nunique()), replace=False))
    cp = predict_all(clean.lines, clean.hierarchy, config.need_states, clean.quality, transaction_ids=tids)
    cpairs = _top_pairs(clean, None)
    rows = []
    total = len(kinds) * len(levels)
    for i, k in enumerate(kinds):
        for j, lv in enumerate(levels):
            rows.append(evaluate_corruption(clean, config, k, lv, seed, sample_receipts, clean_pred=cp, clean_pairs=cpairs))
            if progress:
                progress((i * len(levels) + j + 1) / total)
    return pd.DataFrame(rows)
