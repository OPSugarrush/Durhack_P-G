"""Trend detection with within-consumer permutation null, MDE and honest seasonality status.

Primary test: statistic T_e = sum_r (m_r - mean(m)) * x_re  (a Cochran-Armitage-style trend score)
with the null built by permuting MONTH labels among receipts WITHIN each consumer. That keeps each
consumer's persistent baskets intact, so persistent personal routines cannot masquerade as trends.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from needstate.baskets.construction import BasketMatrix
from needstate.patterns.stats import benjamini_hochberg, minimum_detectable_relative_change, permute_within_groups


def permutation_trend(
    X: np.ndarray,
    month_idx: np.ndarray,
    consumer_idx: np.ndarray,
    n_perm: int = 0,
    seed: int = 0,
) -> dict[str, np.ndarray]:
    """Within-consumer permutation trend test with EXACT moments (no permutation resolution floor).

    X: (receipts, units) binary. Statistic T_e = sum_r (m_r - mbar) x_re.
    Null: month labels permuted among receipts of the same consumer. For consumer c with n_c
    receipts, k_ce receipts containing e and month mean mbar_c:
        E[T_e]   = sum_c k_ce (mbar_c - mbar)
        Var[T_e] = sum_c SSm_c * (k_ce - k_ce^2 / n_c) / (n_c - 1),   SSm_c = sum_r (m_r - mbar_c)^2
    p is two-sided from the normal approximation. (A Monte-Carlo permutation p-value with a
    resolution of 1/(n_perm+1) cannot clear BH correction over ~100 tests unless n_perm is in the
    thousands; the exact-moment form avoids that. Pass n_perm>0 to ALSO return the Monte-Carlo p
    as `p_mc`, used in tests to check the approximation.)
    """
    m = month_idx.astype(float)
    mbar = m.mean()
    mc = m - mbar
    Xf = X.astype(float)
    T = mc @ Xf
    ss = float((mc**2).sum())
    uc, ci = np.unique(consumer_idx, return_inverse=True)
    n_c = np.bincount(ci).astype(float)
    mbar_c = np.bincount(ci, weights=m) / n_c
    ssm_c = np.bincount(ci, weights=(m - mbar_c[ci]) ** 2)
    K = np.zeros((len(uc), X.shape[1]))
    np.add.at(K, ci, Xf)
    mean = (mbar_c - mbar) @ K
    denom = np.where(n_c > 1, n_c - 1, np.inf)
    var = (ssm_c / denom) @ (K - K**2 / n_c[:, None])
    z = np.where(var > 1e-12, (T - mean) / np.sqrt(np.where(var > 1e-12, var, 1)), 0.0)
    out = {"T": T, "slope": T / ss if ss > 0 else np.zeros_like(T), "z": z, "p": 2 * norm.sf(np.abs(z)), "var": var, "mean": mean}
    if n_perm > 0:
        rng = np.random.default_rng(seed)
        exceed = np.zeros(X.shape[1])
        for _ in range(n_perm):
            mp = permute_within_groups(m, consumer_idx, rng)
            Tp = (mp - mbar) @ Xf
            exceed += np.abs(Tp - mean) >= np.abs(T - mean) - 1e-9
        out["p_mc"] = (1.0 + exceed) / (1.0 + n_perm)
    return out


def seasonality_status(n_months: int, min_cycles: int = 2) -> str:
    """Seasonality is assessable only with >= min_cycles full annual cycles of data."""
    if n_months >= 12 * min_cycles:
        return "assessable"
    return f"unassessable ({n_months} months < {12 * min_cycles} needed; seasonal and emerging effects are confounded)"


def trend_scan(
    bm: BasketMatrix,
    n_perm: int = 0,
    seed: int = 0,
    alpha: float = 0.05,
    min_support: int = 20,
    min_cycles: int = 2,
) -> pd.DataFrame:
    """One row per entity at bm.level. Includes MDE next to every claim."""
    X = bm.X
    n_r = X.shape[0]
    counts = X.sum(0)
    keep = counts >= min_support
    res = permutation_trend(X[:, keep], bm.month_idx, bm.consumer_idx, n_perm=n_perm, seed=seed)
    ents = np.array(bm.entities)[keep]
    n_months = len(bm.month_labels)
    k = max(1, n_months // 2)
    first = bm.month_idx < k
    last = bm.month_idx >= n_months - k
    n_a, n_b = int(first.sum()), int(last.sum())
    prev = counts[keep] / n_r
    p_first = X[first][:, keep].mean(0)
    p_last = X[last][:, keep].mean(0)
    df = pd.DataFrame(
        {
            "entity": ents,
            "level": bm.level,
            "receipts_with": counts[keep],
            "prevalence": prev,
            "slope_pp_per_month": res["slope"] * 100,
            "first_half_prev": p_first,
            "second_half_prev": p_last,
            "relative_change_halves": np.where(p_first > 0, (p_last - p_first) / np.where(p_first > 0, p_first, 1), np.nan),
            "p_perm": res["p"],
        }
    )
    df["q"] = benjamini_hochberg(df["p_perm"].to_numpy())
    df["significant"] = df["q"] < alpha
    if n_months < 2:
        df["significant"] = False
        df["p_perm"] = 1.0
        df["q"] = 1.0
    df["direction"] = np.where(df["slope_pp_per_month"] > 0, "up", "down")
    df["mde_relative"] = [
        minimum_detectable_relative_change(max(pf, 1e-4), n_a, n_b) for pf in df["first_half_prev"]
    ]
    df["claim_above_mde"] = df["relative_change_halves"].abs() >= df["mde_relative"]
    df["seasonality"] = seasonality_status(n_months, min_cycles)
    df["test_method"] = "normal approximation using exact within-consumer permutation moments"
    df["mde_basis"] = "approximate independent two-sample planning estimate; no cluster or FDR adjustment"
    df["identifiable_consumers"] = int((np.bincount(bm.consumer_idx) > 1).sum())
    return df.sort_values("p_perm").reset_index(drop=True)


def hierarchical_scan(
    scans: dict[str, pd.DataFrame],
    parent_of: dict[str, dict[str, str]],
    levels: list[str],
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Parent-gated exploration with global Bonferroni control for descendants.

    Root q-values are BH-adjusted. All descendant hypotheses count toward a
    Bonferroni denominator BEFORE selecting parents. This conservative scheme
    avoids claiming a selective-FDR guarantee for pooled selected children.
    """
    out = []
    sel_parents: set[str] | None = None
    tested_parents = 0
    for i, lvl in enumerate(levels):
        df = scans[lvl].copy()
        if i == 0:
            df["tested"] = True
            df["q_hier"] = df["q"]
            df["significant_hier"] = df["significant"]
        else:
            par = df["entity"].map(parent_of[lvl])
            df["parent"] = par
            df["tested"] = par.isin(sel_parents)
            sub = df[df["tested"]]
            n_descendants = sum(len(scans[v]) for v in levels[1:])
            adj_alpha = alpha
            q = np.minimum(sub["p_perm"].to_numpy() * max(n_descendants, 1), 1.0)
            df["q_hier"] = np.nan
            df.loc[sub.index, "q_hier"] = q
            df["significant_hier"] = df["q_hier"] < adj_alpha
        out.append(df)
        sel_parents = set(df.loc[df["significant_hier"], "entity"])
        tested_parents = int(df["tested"].sum())
    return pd.concat(out, ignore_index=True)


def brand_share_decomposition(lines: pd.DataFrame, brand: str, category: str) -> pd.DataFrame:
    """Split brand receipt-prevalence change into CATEGORY GROWTH vs SHARE-OF-CATEGORY change.

    b = c * s  (brand prevalence = category prevalence x brand's share among category buyers), so
    delta b = (c1 - c0) * s0  [category growth]  +  c1 * (s1 - s0)  [share change]. Exact.
    Compares the first half of observed months with the second half.
    """
    d = lines.copy()
    d["_m"] = d["timestamp"].dt.to_period("M")
    months = sorted(d["_m"].unique())
    if len(months) < 2:
        return pd.DataFrame([{"brand": brand, "category": category, "status": "At least two months required"}])
    half = len(months) // 2
    first_set, last_set = set(months[:half]), set(months[-half:])
    rec = d.groupby("transaction_id")["_m"].first()
    in_cat = d[d["category"] == category].groupby("transaction_id").size().reindex(rec.index, fill_value=0) > 0
    in_brand = (
        d[(d["category"] == category) & (d["brand"] == brand)].groupby("transaction_id").size().reindex(rec.index, fill_value=0)
        > 0
    )

    def stats(mset: set) -> tuple[float, float, float]:
        sel = rec.isin(mset)
        n = sel.sum()
        c = in_cat[sel].sum() / n
        b = in_brand[sel].sum() / n
        return c, (b / c if c > 0 else np.nan), b

    c0, s0, b0 = stats(first_set)
    c1, s1, b1 = stats(last_set)
    return pd.DataFrame(
        [
            {
                "brand": brand,
                "category": category,
                "brand_prev_first": b0,
                "brand_prev_last": b1,
                "delta_brand": b1 - b0,
                "from_category_growth": (c1 - c0) * s0,
                "from_share_change": c1 * (s1 - s0),
                "category_prev_first": c0,
                "category_prev_last": c1,
                "share_first": s0,
                "share_last": s1,
            }
        ]
    )
