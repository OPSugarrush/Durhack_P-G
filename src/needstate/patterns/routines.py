"""Consumer-level routine structure (a different unit from basket-level missions).

The honest signal in receipt data is often consumer routines: persistent personal baskets.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from needstate.baskets.construction import BasketMatrix


def concentration(bm: BasketMatrix) -> tuple[pd.DataFrame, dict]:
    """Herfindahl concentration of each consumer's purchases vs the pooled market.

    ratio >> 1 means consumers are far more concentrated than the pooled dataset, i.e. baskets
    are driven by consumer identity and basket-level lift would mostly rediscover consumer profiles.
    """
    X = bm.X.astype(float)
    pooled = X.sum(0)
    pooled_hhi = float(((pooled / pooled.sum()) ** 2).sum())
    rows = []
    for c in np.unique(bm.consumer_idx):
        sel = bm.consumer_idx == c
        if pd.isna(bm.receipts.loc[sel, "customer_id"].iloc[0]):
            continue
        v = X[sel].sum(0)
        if v.sum() == 0:
            continue
        sh = v / v.sum()
        rows.append(
            {
                "consumer_idx": int(c),
                "customer_id": bm.receipts.loc[sel, "customer_id"].iloc[0],
                "n_receipts": int(sel.sum()),
                "hhi": float((sh**2).sum()),
                "distinct_entities": int((v > 0).sum()),
                "repeat_entity_share": float(((X[sel].sum(0)) >= 2).sum() / max((v > 0).sum(), 1)),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=["consumer_idx", "customer_id", "n_receipts", "hhi", "distinct_entities", "repeat_entity_share"])
    summary = {
        "pooled_hhi": pooled_hhi,
        "mean_consumer_hhi": float(df["hhi"].mean()),
        "concentration_ratio": float(df["hhi"].mean() / pooled_hhi),
        "mean_repeat_entity_share": float(df["repeat_entity_share"].mean()),
    }
    return df, summary


def repeat_rates(bm: BasketMatrix, min_receipts: int = 3) -> pd.DataFrame:
    """Per entity: share of its buyers who bought it on >=2 receipts (observed repeat, nothing inferred)."""
    X = bm.X
    ents = np.array(bm.entities)
    rows = []
    for e, name in enumerate(ents):
        known = bm.receipts["customer_id"].notna().to_numpy()
        counts = np.bincount(bm.consumer_idx[known], minlength=int(bm.consumer_idx.max()) + 1)
        per = np.bincount(bm.consumer_idx[known], weights=X[known, e], minlength=len(counts))
        per[counts < min_receipts] = 0
        buyers = per > 0
        if buyers.sum() == 0:
            continue
        rows.append(
            {
                "entity": name,
                "buyers": int(buyers.sum()),
                "repeat_buyers": int((per >= 2).sum()),
                "repeat_rate": float((per[buyers] >= 2).mean()),
            }
        )
    return pd.DataFrame(rows, columns=["entity", "buyers", "repeat_buyers", "repeat_rate"]).sort_values("repeat_rate", ascending=False).reset_index(drop=True)
