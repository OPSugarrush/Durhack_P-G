"""Reconciliation and missingness checks. Flag-and-continue: never crash on bad rows."""
from __future__ import annotations

import numpy as np
import pandas as pd


def reconcile(lines: pd.DataFrame, tol: float = 0.011) -> dict:
    """Run the arithmetic checks the strategy doc requires on any new dataset."""
    line_mismatch = (lines["quantity"] * lines["unit_price"] - lines["line_total"]).abs() > tol
    out = {
        "n_lines": int(len(lines)),
        "n_receipts": int(lines["transaction_id"].nunique()),
        "n_consumers": int(lines["customer_id"].nunique()) if lines["customer_id"].notna().any() else 0,
        "line_total_mismatches": int(line_mismatch.sum()),
        "duplicate_rows": int(lines.duplicated(subset=["transaction_id", "raw_product_text", "line_number"]).sum()),
    }
    if lines["receipt_total"].notna().any():
        sums = lines.groupby("transaction_id")["line_total"].sum()
        totals = lines.groupby("transaction_id")["receipt_total"].first()
        out["receipt_total_mismatches"] = int(((sums - totals).abs() > tol).sum())
    out["missingness"] = {c: float(v) for c, v in lines.isna().mean().items() if v > 0}
    return out


def receipt_quality(lines: pd.DataFrame, resolved_col: str = "family_id", tol: float = 0.011) -> pd.DataFrame:
    """Per-receipt data_completeness (0-1). Kept separate from model confidence on purpose."""
    resolved = lines[resolved_col].notna() if resolved_col in lines else lines["raw_product_text"].notna()
    g = lines.assign(
        _resolved=resolved,
        _arith_ok=(lines["quantity"] * lines["unit_price"] - lines["line_total"]).abs() <= tol,
        _price_ok=lines["unit_price"].notna() & (lines["unit_price"] > 0),
    ).groupby("transaction_id")
    q = pd.DataFrame(
        {
            "resolved_share": g["_resolved"].mean(),
            "arith_ok_share": g["_arith_ok"].mean(),
            "price_ok_share": g["_price_ok"].mean(),
            "n_lines": g.size(),
        }
    )
    if lines["receipt_total"].notna().any():
        sums = g["line_total"].sum()
        totals = g["receipt_total"].first()
        q["total_ok"] = ((sums - totals).abs() <= tol).astype(float)
    else:
        q["total_ok"] = np.nan
    q["data_completeness"] = q[["resolved_share", "arith_ok_share", "price_ok_share", "total_ok"]].mean(axis=1)
    q["data_completeness"] *= q["resolved_share"]
    return q


def month_index(timestamps: pd.Series) -> tuple[np.ndarray, list[str]]:
    """0-based consecutive month index and labels, anchored on the first observed month."""
    per = timestamps.dt.to_period("M")
    first = per.min()
    idx = np.array([(p - first).n for p in per], dtype=int)
    labels = [str(first + i) for i in range(int(idx.max()) + 1)]
    return idx, labels
