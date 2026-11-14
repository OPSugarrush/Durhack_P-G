import numpy as np

from needstate.patterns.cooccurrence import naive_pairs, null_model_pairs
from needstate.patterns.stats import benjamini_hochberg, minimum_detectable_relative_change
from needstate.patterns.trends import hierarchical_scan, permutation_trend, seasonality_status, trend_scan
from tests.helpers import synthetic_bm


def test_bh_monotone_and_bounded():
    q = benjamini_hochberg(np.array([0.001, 0.04, 0.03, 0.5]))
    assert np.all(q <= 1) and np.all(q >= np.array([0.001, 0.04, 0.03, 0.5]) - 1e-12)
    assert np.allclose(q, [0.004, 0.0533333333, 0.0533333333, 0.5])


def test_mde_matches_hand_arithmetic():
    mde = minimum_detectable_relative_change(0.05, 1500, 1500)
    assert 0.40 < mde < 0.55                      # ~45-50%: strategy review quoted 40-45% roughly
    assert minimum_detectable_relative_change(0.01, 1500, 1500) > 1.5 * mde


def test_trend_exact_moments_match_monte_carlo():
    bm = synthetic_bm(seed=1)
    res = permutation_trend(bm.X[:, :12], bm.month_idx, bm.consumer_idx, n_perm=800, seed=2)
    assert np.abs(res["p"] - res["p_mc"]).max() < 0.08


def test_no_trend_data_has_no_fdr_discoveries():
    flagged = [int(trend_scan(synthetic_bm(seed=s)).significant.sum()) for s in range(5)]
    assert sum(flagged) <= 1                       # at most a rare false alarm across 5 null datasets


def test_injected_trend_is_found():
    bm = synthetic_bm(seed=3, trend_product=4, trend_strength=0.5)
    sc = trend_scan(bm)
    row = sc[sc.entity == "p4"].iloc[0]
    assert row.significant and row.direction == "up"


def test_seasonality_unassessable_under_two_years():
    assert seasonality_status(6).startswith("unassessable")
    assert seasonality_status(24) == "assessable"


def test_null_model_calibrated_and_naive_lift_confounded():
    bm = synthetic_bm(seed=5)                       # persistent baskets, NO planted co-purchase
    nm = null_model_pairs(bm, min_count=8)
    naive = naive_pairs(bm, 8)["naive_lift"]
    assert naive.max() > 1.25                       # consumer identity inflates naive lift
    assert 0.9 < nm["adj_lift"].median() < 1.1      # null removes it
    assert (nm["q"] < 0.05).sum() <= 0.02 * len(nm) + 2


def test_null_model_detects_planted_bundle():
    # 45 hypotheses let 999 randomisations resolve an isolated 5% BH discovery.
    bm = synthetic_bm(seed=6, n_products=10, bundle=(2, 7), bundle_rate=0.15)
    nm = null_model_pairs(bm, min_count=8)
    top = nm.iloc[0]
    assert {top.family_a, top.family_b} == {"p2", "p7"} and top.q < 0.05


def test_hierarchical_scan_only_tests_children_of_significant_parents():
    bm = synthetic_bm(seed=3, trend_product=4, trend_strength=0.5)
    fam = trend_scan(bm)
    parents = {e: ("A" if e in {"p4", "p5"} else "B") for e in fam.entity}
    import pandas as pd
    par = pd.DataFrame({"entity": ["A", "B"], "p_perm": [0.0001, 0.9], "q": [0.0002, 0.9], "significant": [True, False]})
    out = hierarchical_scan({"cat": par, "fam": fam}, {"fam": parents}, ["cat", "fam"])
    fam_out = out[out.get("parent").notna()]
    assert set(fam_out[fam_out.tested].parent) == {"A"}
