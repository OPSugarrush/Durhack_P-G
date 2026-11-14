"""Statistical helpers: FDR, power / minimum detectable effect, permutation machinery."""
from __future__ import annotations

import numpy as np
from scipy.stats import norm


def benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    """BH-adjusted q-values (monotone). NaNs propagate."""
    p = np.asarray(p, dtype=float)
    q = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    pv = p[ok]
    n = len(pv)
    if n == 0:
        return q
    order = np.argsort(pv)
    ranked = pv[order] * n / (np.arange(n) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(ranked, 1.0)
    q[ok] = out
    return q


def minimum_detectable_relative_change(
    base_prevalence: float, n_a: int, n_b: int, alpha: float = 0.05, power: float = 0.8
) -> float:
    """Smallest RELATIVE increase in a proportion detectable in an n_a vs n_b two-sample z-test.

    Returns np.inf if no increase up to prevalence 1.0 is detectable.
    """
    p0 = float(base_prevalence)
    if p0 <= 0 or n_a <= 0 or n_b <= 0:
        return float("inf")
    za, zb = norm.ppf(1 - alpha / 2), norm.ppf(power)

    def needed(p1: float) -> float:
        se = np.sqrt(p0 * (1 - p0) / n_a + p1 * (1 - p1) / n_b)
        return (za + zb) * se

    lo, hi = 0.0, (1.0 - p0) / p0
    if (p0 * (1 + hi) - p0) < needed(min(p0 * (1 + hi), 1.0)):
        return float("inf")
    for _ in range(60):
        mid = (lo + hi) / 2
        p1 = p0 * (1 + mid)
        if (p1 - p0) >= needed(p1):
            hi = mid
        else:
            lo = mid
    return hi


def permute_within_groups(values: np.ndarray, groups: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Return `values` shuffled within each group (groups need not be sorted)."""
    order = np.lexsort((rng.random(len(values)), groups))
    sorted_groups_idx = np.argsort(groups, kind="stable")
    out = np.empty_like(values)
    out[sorted_groups_idx] = values[order]
    return out
