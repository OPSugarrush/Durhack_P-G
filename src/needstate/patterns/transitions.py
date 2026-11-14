"""Observed entry and exit between adjacent receipts; no preference or motive claims."""
import numpy as np
import pandas as pd


def entry_exit(bm):
    counts = np.zeros((len(bm.entities), 4), dtype=int)
    comparable = 0
    for _, group in bm.receipts.dropna(subset=["customer_id"]).groupby("customer_id"):
        if len(group) < 2:
            continue
        order = group.sort_values(["timestamp", "transaction_id"]).index.to_numpy()
        before, after = bm.X[order[:-1]].astype(bool), bm.X[order[1:]].astype(bool)
        counts[:, 0] += (~before & after).sum(0)
        counts[:, 1] += (before & ~after).sum(0)
        counts[:, 2] += (~before).sum(0)
        counts[:, 3] += before.sum(0)
        comparable += len(order) - 1
    return pd.DataFrame({"entity": bm.entities, "observed_entries": counts[:, 0], "observed_exits": counts[:, 1],
                         "entry_rate": np.divide(counts[:, 0], counts[:, 2], out=np.full(len(counts), np.nan), where=counts[:, 2] > 0),
                         "exit_rate": np.divide(counts[:, 1], counts[:, 3], out=np.full(len(counts), np.nan), where=counts[:, 3] > 0),
                         "comparable_adjacent_receipts": comparable})
