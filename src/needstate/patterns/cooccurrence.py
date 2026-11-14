"""Co-purchase strength with a within-consumer null model and consumer-level bootstrap.

Naive lift on pooled baskets mostly rediscovers consumer profiles (persistent personal baskets).
Null model: for each consumer, pool that consumer's (receipt, entity) incidences and reshuffle the
entities across that consumer's receipts, preserving every receipt's size and every consumer's
product mix. A pair is interesting only to the extent it exceeds what consumer identity explains.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from needstate.baskets.construction import BasketMatrix
from needstate.patterns.stats import benjamini_hochberg, permute_within_groups


def _co(X: np.ndarray) -> np.ndarray:
    Xf = X.astype(np.float32)
    return Xf.T @ Xf


def naive_pairs(bm: BasketMatrix, min_count: int = 5) -> pd.DataFrame:
    X = bm.X
    n = X.shape[0]
    cnt = X.sum(0).astype(float)
    co = _co(X)
    iu = np.triu_indices(len(bm.entities), k=1)
    c = co[iu]
    keep = c >= min_count
    a, b, c = iu[0][keep], iu[1][keep], c[keep]
    lift = c * n / (cnt[a] * cnt[b])
    ents = np.array(bm.entities)
    return pd.DataFrame(
        {"family_a": ents[a], "family_b": ents[b], "count": c.astype(int), "naive_lift": lift, "_i": a, "_j": b}
    )


def curveball_trade(rows: list[set[int]], rng: np.random.Generator) -> None:
    """One reversible trade preserves binary row and column margins exactly."""
    if len(rows) < 2:
        return
    i, j = rng.choice(len(rows), 2, replace=False)
    a, b = rows[i], rows[j]
    common = a & b
    left, right = a - b, b - a
    pool = np.array(sorted(left | right), dtype=int)
    if len(pool) < 2:
        return
    rng.shuffle(pool)
    rows[i] = common | set(pool[:len(left)].tolist())
    rows[j] = common | set(pool[len(left):].tolist())


def null_model_pairs(bm: BasketMatrix, n_perm: int = 999, seed: int = 0, min_count: int = 8) -> pd.DataFrame:
    """Fixed-margin Curveball null within consumers; Monte Carlo p and BH q.

    Every draw preserves each receipt size and each consumer's product frequencies.
    Draws follow 10 burn-in sweeps and two sweeps between samples. Finite-chain
    mixing is a limitation: repeat across seeds before commercial interpretation.
    BH includes ALL possible pairs; support filtering happens only after correction.
    Unknown consumers have singleton blocks and contribute no randomisable evidence.
    """
    if n_perm < 1:
        raise ValueError("n_perm must be positive")
    rng = np.random.default_rng(seed)
    E = bm.X.shape[1]
    I, J = np.triu_indices(E, 1)
    obs = _co(bm.X)[I, J]
    groups = [np.flatnonzero(bm.consumer_idx == c) for c in np.unique(bm.consumer_idx)]
    groups = [g for g in groups if len(g) > 1]
    xn = bm.X.astype(bool).copy()
    lengths = np.array([len(g) for g in groups], dtype=int)
    padded = np.zeros((len(groups), max(lengths, default=1)), dtype=int)
    for k, g in enumerate(groups):
        padded[k, :len(g)] = g
    def sweep(n=1):
        # One trade per consumer per round, batched in NumPy. Consumer blocks
        # are disjoint, so these independent trades commute exactly.
        if not len(groups):
            return
        for _ in range(n * int(lengths.max())):
            ia = rng.integers(0, lengths)
            ib = rng.integers(0, lengths - 1)
            ib += ib >= ia
            ar = padded[np.arange(len(groups)), ia]
            br = padded[np.arange(len(groups)), ib]
            aa, bb = xn[ar], xn[br]
            common = aa & bb
            exclusive = aa ^ bb
            left_n = (aa & ~bb).sum(1)
            keys = rng.random(exclusive.shape)
            keys[~exclusive] = 2.0
            order = np.argsort(keys, axis=1)
            choose = np.zeros_like(exclusive)
            choose[np.arange(len(groups))[:, None], order] = np.arange(E)[None, :] < left_n[:, None]
            choose &= exclusive
            xn[ar] = common | choose
            xn[br] = common | (exclusive & ~choose)
    sweep(10)
    total = np.zeros(len(I)); ge = np.zeros(len(I))
    for _ in range(n_perm):
        sweep(2)
        xf = xn.astype(np.float32)
        values = (xf.T @ xf)[I, J]
        total += values
        ge += values >= obs - 1e-9
    mu = total / n_perm
    pv = (1 + ge) / (1 + n_perm)
    counts = bm.X.sum(0).astype(float)
    denom = counts[I] * counts[J]
    lift = np.divide(obs * bm.n_receipts, denom, out=np.full(len(I), np.nan), where=denom > 0)
    adjusted = np.divide(obs, mu, out=np.full(len(I), np.nan), where=mu > 0)
    out = pd.DataFrame({"family_a": np.array(bm.entities)[I], "family_b": np.array(bm.entities)[J],
                        "count": obs.astype(int), "naive_lift": lift, "_i": I, "_j": J,
                        "null_mean": mu, "excess": obs - mu, "adj_lift": adjusted,
                        "p_perm": pv, "q": benjamini_hochberg(pv),
                        "null_method": "within-consumer fixed-margin Curveball",
                        "permutations": n_perm, "p_resolution": 1 / (n_perm + 1)})
    return out[out["count"] >= min_count].sort_values(["q", "p_perm", "adj_lift"], ascending=[True, True, False]).reset_index(drop=True)


def bootstrap_pair_ci(
    bm: BasketMatrix, pairs: pd.DataFrame, n_boot: int = 500, seed: int = 0, level: float = 0.95
) -> pd.DataFrame:
    """Consumer-level bootstrap CI for naive lift of selected pairs (pairs need _i/_j columns)."""
    rng = np.random.default_rng(seed)
    cons = bm.consumer_idx
    uc = np.unique(cons)
    pos = {c: k for k, c in enumerate(uc)}
    ci = np.array([pos[c] for c in cons])
    I, J = pairs["_i"].to_numpy(), pairs["_j"].to_numpy()
    n_c = len(uc)
    per_n = np.bincount(ci, minlength=n_c).astype(float)
    per_a = np.zeros((n_c, len(pairs)))
    per_b = np.zeros((n_c, len(pairs)))
    per_ab = np.zeros((n_c, len(pairs)))
    X = bm.X.astype(float)
    for k, (i, j) in enumerate(zip(I, J)):
        np.add.at(per_a[:, k], ci, X[:, i])
        np.add.at(per_b[:, k], ci, X[:, j])
        np.add.at(per_ab[:, k], ci, X[:, i] * X[:, j])
    weights = rng.multinomial(n_c, np.full(n_c, 1 / n_c), size=n_boot).astype(float)
    ns = weights @ per_n
    a, bb, ab = weights @ per_a, weights @ per_b, weights @ per_ab
    denom = a * bb
    lifts = np.divide(ab * ns[:, None], denom, out=np.full_like(ab, np.nan), where=denom > 0)
    lo, hi = (1 - level) / 2, 1 - (1 - level) / 2
    out = pairs.copy()
    out["lift_ci_low"] = np.nanquantile(lifts, lo, axis=0)
    out["lift_ci_high"] = np.nanquantile(lifts, hi, axis=0)
    return out
