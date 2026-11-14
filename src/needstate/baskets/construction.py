"""Line items -> basket matrices at any hierarchy level."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from needstate.product_intel.hierarchy import entity_column
from needstate.validation.checks import month_index


@dataclass
class BasketMatrix:
    level: str
    entities: list[str]
    receipts: pd.DataFrame      # one row per receipt: transaction_id, customer_id, retailer_id, timestamp, month
    X: np.ndarray               # (n_receipts, n_entities) uint8 binary presence
    month_idx: np.ndarray       # (n_receipts,)
    month_labels: list[str]
    consumer_idx: np.ndarray    # (n_receipts,) integer codes; -1 never used (unknown consumers get unique codes)

    @property
    def n_receipts(self) -> int:
        return self.X.shape[0]


def build_basket_matrix(lines: pd.DataFrame, level: str = "family") -> BasketMatrix:
    col = entity_column(level)
    d = lines.dropna(subset=[col])
    receipts = (
        lines.groupby("transaction_id", sort=True)
        .agg(customer_id=("customer_id", "first"), retailer_id=("retailer_id", "first"), timestamp=("timestamp", "first"))
        .reset_index()
    )
    mi, labels = month_index(receipts["timestamp"])
    receipts["month"] = mi
    pres = (
        d.drop_duplicates(["transaction_id", col])
        .assign(v=1)
        .pivot_table(index="transaction_id", columns=col, values="v", fill_value=0, aggfunc="max")
        .reindex(receipts["transaction_id"], fill_value=0)
    )
    # receipts with unknown consumer each get their own code so they never share a null-model block
    cons = receipts["customer_id"].astype("object")
    unknown = cons.isna()
    codes = pd.factorize(cons.where(~unknown, other=None))[0].astype(int)
    if unknown.any():
        start = codes.max() + 1 if len(codes) else 0
        codes[unknown.to_numpy()] = np.arange(start, start + int(unknown.sum()))
    return BasketMatrix(
        level=level,
        entities=[str(c) for c in pres.columns],
        receipts=receipts,
        X=pres.to_numpy(dtype=np.uint8),
        month_idx=mi,
        month_labels=labels,
        consumer_idx=codes,
    )
