"""Synthetic-injection validation: the engine's answer to 'no ground truth'.

Inject known trends and bundles into the real data at several strengths, then report
(a) which strengths are recovered and (b) the false-alarm rate on un-injected data.
Operates on a canonical+family line table (needs family_id, hierarchy columns).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from needstate.baskets.construction import build_basket_matrix
from needstate.patterns.trends import trend_scan, permutation_trend
from needstate.patterns.stats import benjamini_hochberg, permute_within_groups
from needstate.validation.checks import month_index

_HIER_COLS = ["family_id", "brand", "owner", "function", "category", "department"]


def _receipt_frame(lines: pd.DataFrame) -> pd.DataFrame:
    r = lines.groupby("transaction_id").agg(
        customer_id=("customer_id", "first"),
        retailer_id=("retailer_id", "first"),
        timestamp=("timestamp", "first"),
        line_number=("line_number", "max"),
    )
    r["month"], _ = month_index(r["timestamp"])
    return r


def _clone_lines(lines: pd.DataFrame, receipts: pd.DataFrame, tids: np.ndarray, family: str, tag: str) -> pd.DataFrame:
    """Create one synthetic line of `family` on each receipt in tids."""
    tmpl = lines[lines["family_id"] == family].iloc[0]
    price = float(lines.loc[lines["family_id"] == family, "unit_price"].median())
    base = receipts.loc[tids]
    new = pd.DataFrame(
        {
            "line_id": [f"{t}-inj-{tag}" for t in tids],
            "transaction_id": tids,
            "customer_id": base["customer_id"].to_numpy(),
            "retailer_id": base["retailer_id"].to_numpy(),
            "timestamp": base["timestamp"].to_numpy(),
            "raw_product_text": tmpl["raw_product_text"],
            "quantity": 1,
            "unit_price": price,
            "line_total": price,
            "line_number": base["line_number"].to_numpy() + 1,
            "family_id": family,
        }
    )
    for c in _HIER_COLS[1:]:
        new[c] = tmpl[c]
    new["injected"] = True
    return new


def inject_trend(lines: pd.DataFrame, family: str, strength: float, seed: int = 0) -> pd.DataFrame:
    """Linear ramp: extra prevalence rises 0 -> `strength` (absolute) from first to last month."""
    rng = np.random.default_rng(seed)
    rec = _receipt_frame(lines)
    has = set(lines.loc[lines["family_id"] == family, "transaction_id"])
    cand = rec.loc[~rec.index.isin(has)]
    ramp = cand["month"] / max(int(rec["month"].max()), 1)
    # strength is absolute prevalence added at the end of the period, among ALL receipts
    p_add = np.clip(strength / max(1 - len(has) / len(rec), 1e-6) * ramp, 0, 1)
    take = cand.index.to_numpy()[rng.random(len(cand)) < p_add.to_numpy()]
    out = pd.concat([lines.assign(injected=False), _clone_lines(lines, rec, take, family, "t")], ignore_index=True)
    return out


def inject_bundle(lines: pd.DataFrame, families: list[str], rate: float, start_month: int, seed: int = 0) -> pd.DataFrame:
    """From start_month on, a fraction `rate` of receipts gains the whole bundle."""
    rng = np.random.default_rng(seed)
    rec = _receipt_frame(lines)
    cand = rec[rec["month"] >= start_month]
    chosen = cand.index.to_numpy()[rng.random(len(cand)) < rate]
    parts = [lines.assign(injected=False)]
    for k, f in enumerate(families):
        have = set(lines.loc[lines["family_id"] == f, "transaction_id"])
        parts.append(_clone_lines(lines, rec, np.array([t for t in chosen if t not in have]), f, f"b{k}"))
    return pd.concat(parts, ignore_index=True)


def false_alarm_rate(lines: pd.DataFrame, n_seeds: int = 5, n_perm: int = 0, alpha: float = 0.05) -> dict:
    """Run the trend scan on data with month labels shuffled across CONSUMERS' receipts (true null)
    and on the raw data; report the share of entities flagged significant after FDR."""
    bm = build_basket_matrix(lines, "family")
    rng = np.random.default_rng(0)
    flagged = []
    for s in range(n_seeds):
        m = bm.month_idx.copy()
        # global shuffle of month labels destroys any real time structure
        bm2 = type(bm)(**{**bm.__dict__, "month_idx": permute_within_groups(m, bm.consumer_idx, rng)})
        flagged.append(int(trend_scan(bm2, n_perm=n_perm, seed=s, alpha=alpha)["significant"].sum()))
    raw = trend_scan(bm, n_perm=n_perm, seed=99, alpha=alpha)
    return {
        "entities_tested": int(len(raw)),
        "organic_significant_trends": int(raw["significant"].sum()),
        "organic_p_below_0.05_uncorrected": int((raw["p_perm"] < 0.05).sum()),
        "shuffled_null_flags_per_scan": flagged,
        "shuffled_null_false_alarm_scans": int(sum(f > 0 for f in flagged)),
        "n_scans": n_seeds,
    }


def trend_recovery(
    lines: pd.DataFrame,
    strengths: tuple[float, ...] = (0.01, 0.02, 0.04, 0.08),
    n_trials: int = 8,
    n_perm: int = 0,
    alpha: float = 0.05,
    seed: int = 0,
    min_prevalence: float = 0.02,
) -> pd.DataFrame:
    """Recovery rate of an injected upward ramp by absolute end-of-period prevalence added."""
    rng = np.random.default_rng(seed)
    fam_prev = lines.groupby("family_id")["transaction_id"].nunique() / lines["transaction_id"].nunique()
    pool = fam_prev[(fam_prev >= min_prevalence) & (fam_prev <= 0.15)].index.to_numpy()
    rows = []
    for st in strengths:
        hits = 0
        for t in range(n_trials):
            fam = str(rng.choice(pool))
            inj = inject_trend(lines, fam, st, seed=int(rng.integers(1e9)))
            bm = build_basket_matrix(inj, "family")
            sc = trend_scan(bm, n_perm=n_perm, seed=t, alpha=alpha)
            row = sc[sc["entity"] == fam]
            hits += int(len(row) and bool(row["significant"].iloc[0]) and row["direction"].iloc[0] == "up")
        rows.append({"added_prevalence_pp": st * 100, "trials": n_trials, "recovered": hits, "recovery_rate": hits / n_trials})
    return pd.DataFrame(rows)


def bundle_recovery(
    lines: pd.DataFrame,
    pairs: list[tuple[str, str]],
    rates: tuple[float, ...] = (0.01, 0.02, 0.04, 0.08),
    start_month: int = 3,
    n_perm: int = 0,
    alpha: float = 0.05,
    seed: int = 0,
) -> pd.DataFrame:
    """Detect an injected 2-product bundle emerging mid-period via the pair-indicator trend test."""
    rng = np.random.default_rng(seed)
    rows = []
    for rate in rates:
        hits = 0
        for k, (a, b) in enumerate(pairs):
            inj = inject_bundle(lines, [a, b], rate, start_month, seed=int(rng.integers(1e9)))
            bm = build_basket_matrix(inj, "family")
            ia, ib = bm.entities.index(a), bm.entities.index(b)
            iu = np.triu_indices(len(bm.entities), 1)
            co = (bm.X[:, iu[0]] * bm.X[:, iu[1]])
            keep = co.sum(0) >= 20
            res = permutation_trend(co[:, keep], bm.month_idx, bm.consumer_idx, n_perm=n_perm, seed=k)
            q = benjamini_hochberg(res["p"])
            target = np.where((iu[0][keep] == ia) & (iu[1][keep] == ib) | (iu[0][keep] == ib) & (iu[1][keep] == ia))[0]
            hits += int(len(target) and q[target[0]] < alpha and res["slope"][target[0]] > 0)
        rows.append({"bundle_rate": rate, "trials": len(pairs), "recovered": hits, "recovery_rate": hits / len(pairs)})
    return pd.DataFrame(rows)
