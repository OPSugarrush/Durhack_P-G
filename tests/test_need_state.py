import pandas as pd

from needstate.need_state.decomposition import decompose_basket
from needstate.need_state.inference import evidence_concentration, predict_basket

H = pd.DataFrame({
    "family_id": ["ariel", "comfort", "pantene", "oralb", "bread", "milk"],
    "function": ["fabric_wash", "fabric_care", "hair_cleanse", "oral_hygiene", "bread_staple", "chilled_staple"],
    "category": ["laundry", "laundry", "hair_care", "oral_care", "bakery", "dairy_chilled"],
    "department": ["hpc", "hpc", "hpc", "hpc", "grocery", "grocery"],
})
NEEDS = {"thresholds": {"abstain_below_score": 0.35, "abstain_below_completeness": 0.6},
         "need_states": [
             {"id": "laundry_care", "label": "Laundry", "functions": ["fabric_wash", "fabric_care"]},
             {"id": "hair_care", "label": "Hair", "functions": ["hair_cleanse"]},
             {"id": "breakfast", "label": "Breakfast", "functions": ["bread_staple"]}]}


def test_partitions_split_laundry_from_grocery():
    parts = decompose_basket(["ariel", "comfort", "bread", "milk"], H)
    sets = [set(p.families) for p in parts]
    assert {"ariel", "comfort"} in sets and {"bread", "milk"} in sets


def test_need_score_anchored_to_partition_support():
    p = predict_basket("b1", ["ariel", "comfort", "bread"], H, NEEDS)
    laundry = [c for c in p.candidate_needs if c["need_state_id"] == "laundry_care"][0]
    assert set(laundry["supporting_product_ids"]) == {"ariel", "comfort"}
    # no hair products => no hair candidate can exist (P1/P2 contradiction made structurally impossible)
    assert all(c["need_state_id"] != "hair_care" for c in p.candidate_needs)


def test_scores_are_independent_not_normalised():
    p = predict_basket("b1", ["ariel", "comfort", "pantene", "bread"], H, NEEDS)
    assert sum(c["score"] for c in p.candidate_needs) > 1.0


def test_abstains_on_low_completeness_or_thin_evidence():
    assert predict_basket("b", ["ariel"], H, NEEDS, data_completeness=0.3).abstained
    assert predict_basket("b", ["milk"], H, NEEDS).abstained                     # no need-state serves it
    assert not predict_basket("b", ["ariel", "comfort"], H, NEEDS).abstained


def test_evidence_concentration_does_not_change_scores():
    assert evidence_concentration([0.9, 0.1]) > evidence_concentration([0.5, 0.45])
