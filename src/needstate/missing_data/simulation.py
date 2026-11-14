"""Controlled corruption of a clean line table, tagged by missingness MECHANISM (MCAR/MAR/MNAR)."""
from __future__ import annotations

import numpy as np
import pandas as pd

MECHANISM = {
    "drop_lines_mcar": "MCAR",
    "drop_lines_mar_retailer": "MAR",
    "drop_lines_mnar_price": "MNAR",
    "blank_names": "MCAR",
    "drop_customer_ids": "MCAR",
    "drop_receipts": "MCAR",
    "ocr_noise": "MCAR",
    "duplicate_lines": "MCAR",
    "blank_prices": "MCAR",
    "category_loss": "MNAR",
}
_OCR = {"O": "0", "I": "1", "S": "5", "B": "8", "E": "3"}


def corrupt_lines(lines: pd.DataFrame, kind: str, level: float, seed: int = 0) -> pd.DataFrame:
    """Return a corrupted copy. `level` in (0, 1) is the fraction affected (on average)."""
    rng = np.random.default_rng(seed)
    d = lines.copy()
    n = len(d)
    if not 0 <= level <= 1:
        raise ValueError("Corruption level must be between 0 and 1")
    if kind == "blank_prices":
        d.loc[rng.random(n) < level, "unit_price"] = np.nan
        return d
    if kind == "category_loss":
        if "category" not in d:
            raise ValueError("category_loss requires category metadata")
        cats = d["category"].dropna().unique()
        if len(cats):
            target = cats[0]
            return d[~((d["category"] == target) & (rng.random(n) < level))].reset_index(drop=True)
        return d
    if kind == "drop_lines_mcar":
        return d[rng.random(n) >= level].reset_index(drop=True)
    if kind == "drop_lines_mar_retailer":
        rets = sorted(d["retailer_id"].unique())
        mult = {r: (2.0 if i % 2 == 0 else 0.0) for i, r in enumerate(rets)}
        scale = level * len(rets) / max(sum(mult.values()), 1e-9)   # keeps the average drop rate at `level`
        p = d["retailer_id"].map(mult).to_numpy() * scale
        return d[rng.random(n) >= np.clip(p, 0, 1)].reset_index(drop=True)
    if kind == "drop_lines_mnar_price":
        rank = d["unit_price"].rank(pct=True).to_numpy()      # cheap lines are dropped preferentially
        w = (1.0 - rank) + 1e-3
        p = np.clip(w / w.mean() * level, 0, 1)
        return d[rng.random(n) >= p].reset_index(drop=True)
    if kind == "blank_names":
        hit = rng.random(n) < level
        d.loc[hit, "raw_product_text"] = ""
        d.loc[hit, "raw_product_text"] = pd.NA
        return d
    if kind == "drop_customer_ids":
        tids = d["transaction_id"].unique()
        missing = tids[rng.random(len(tids)) < level]
        d.loc[d["transaction_id"].isin(missing), "customer_id"] = pd.NA
        return d
    if kind == "drop_receipts":
        tids = d["transaction_id"].unique()
        gone = set(tids[rng.random(len(tids)) < level])
        return d[~d["transaction_id"].isin(gone)].reset_index(drop=True)
    if kind == "ocr_noise":
        def noisy(s: str) -> str:
            if pd.isna(s):
                return s
            ch = list(s)
            for i, c in enumerate(ch):
                if c in _OCR and rng.random() < level * 0.5:
                    ch[i] = _OCR[c]
            return "".join(ch)
        d["raw_product_text"] = d["raw_product_text"].map(noisy)
        return d
    if kind == "duplicate_lines":
        dup = d[rng.random(n) < level].copy()
        dup["line_id"] = dup["line_id"].astype(str) + "-dup"
        return pd.concat([d, dup], ignore_index=True)
    raise ValueError(f"unknown corruption kind {kind!r}")
