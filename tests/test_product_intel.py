import pandas as pd

from needstate.product_intel.entity_resolution import expand, fold, resolve_products
from needstate.product_intel.hierarchy import build_hierarchy
from needstate.product_intel.portfolio import PortfolioLens

ABBR = {"T/TISSUE": "TOILET TISSUE", "W/UP LIQ": "WASHING UP LIQUID", "WASH LIQ": "WASHING LIQUID"}


def test_fold_keeps_digits_consistent():
    assert fold("0RAL-B 1L") == fold("ORAL-B IL") == "ORAL-B IL"


def test_expand_is_phrase_bounded():
    assert expand("ARIEL WASH LIQ 24 W", ABBR) == "ARIEL WASHING LIQUID 24 W"
    assert expand("WASHING LIQUID", ABBR) == "WASHING LIQUID"   # no double expansion


def test_ocr_abbreviation_and_truncation_resolve_to_one_family():
    counts = pd.Series({
        "ARIEL ORIG WASH LIQ 24 W": 190, "AR1EL 0RIG WASH LIQ 24 W": 10, "ARIEL ORIG WASHING LIQUID 24 W": 88,
        "CUSHELLE ORIG T/TISSUE 4 ROLLS": 238, "CUSHELLE ORIG TOILET TISSUE 4 ROL": 128,
    })
    res = resolve_products(counts, ABBR)
    assert len(res.catalogue) == 2
    assert res.catalogue["n_variants"].sum() == 5


def test_pack_size_variants_never_auto_merge_but_are_reviewed():
    counts = pd.Series({"TILDA PURE BASMATI RICE 1KG": 349, "TILDA PURE BASMATI RICE 2KG": 327})
    res = resolve_products(counts, {}, fuzzy_review_threshold=0.80)
    assert len(res.catalogue) == 2          # different products stay different
    assert len(res.review_pairs) == 1       # ...but a human is asked


def test_hierarchy_nullable_brand_and_owner():
    cat = pd.DataFrame({"family_id": ["a", "b"], "family_name": ["ARIEL X", "BANANAS 5 PK"], "family_key": ["ARIEL X WASHING LIQUID 24 W", "BANANAS 5 PK"]})
    cfg = {"brands": ["ARIEL"], "owners": {"P&G": ["ARIEL"]},
           "rules": [{"pattern": "WASHING LIQUID", "department": "hpc", "category": "laundry", "function": "fabric_wash"},
                     {"pattern": "BANANAS", "department": "grocery", "category": "fresh", "function": "fresh_cooking"}]}
    h = build_hierarchy(cat, cfg).set_index("family_id")
    assert h.loc["a", "owner"] == "P&G" and h.loc["a", "category"] == "laundry"
    assert pd.isna(h.loc["b", "brand"]) and pd.isna(h.loc["b", "owner"])


def test_empty_lens_is_general_market_mode():
    h = pd.DataFrame({"family_id": ["a", "b"], "brand": ["X", None], "owner": [None, None], "function": ["f", "g"], "category": ["c", "c"], "department": ["d", "d"]})
    pairs = pd.DataFrame({"family_a": ["a"], "family_b": ["b"]})
    assert not PortfolioLens().active
    assert PortfolioLens().annotate_pairs(pairs, h)["portfolio_exposure"].isna().all()


def test_lens_exposure_and_adjacency():
    h = pd.DataFrame({"family_id": ["a", "b", "c"], "brand": ["X", "Y", "Z"], "owner": ["P&G", None, None],
                      "function": ["fabric_wash", "fabric_wash", "treat"], "category": ["l", "l", "t"], "department": ["h", "h", "g"]})
    lens = PortfolioLens("P&G", ["P&G"])
    out = lens.annotate_pairs(pd.DataFrame({"family_a": ["a", "b"], "family_b": ["b", "c"]}), h)
    assert out["portfolio_exposure"].tolist() == [0.5, 0.0]
    assert out["portfolio_adjacent"].tolist() == [True, True]
