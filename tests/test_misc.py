import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from needstate.baskets.construction import build_basket_matrix
from needstate.missing_data.simulation import MECHANISM, corrupt_lines
from needstate.reliability import review_queue as rq
from needstate.validation.checks import reconcile
from tests.helpers import mini_lines


def _lines():
    d = mini_lines()
    d["family_id"] = d["raw_product_text"].str[:6]
    d["category"] = "test_category"
    return d


def test_every_corruption_kind_runs_and_is_tagged():
    d = _lines()
    for kind in MECHANISM:
        out = corrupt_lines(d, kind, 0.3, seed=1)
        assert len(out) > 0 and MECHANISM[kind] in {"MCAR", "MAR", "MNAR"}
    assert len(corrupt_lines(d, "duplicate_lines", 0.5, 1)) > len(d)
    assert corrupt_lines(d, "drop_customer_ids", 0.5, 1)["customer_id"].isna().any()


def test_mnar_drops_cheap_lines_more():
    rng = np.random.default_rng(0)
    d = pd.DataFrame({"retailer_id": "X", "unit_price": rng.uniform(0.5, 10, 4000)})
    kept = corrupt_lines(d, "drop_lines_mnar_price", 0.3, 0)
    assert kept["unit_price"].mean() > d["unit_price"].mean()


def test_reconcile_flags_bad_arithmetic():
    d = mini_lines().copy()
    d.loc[0, "line_total"] = 99
    assert reconcile(d)["line_total_mismatches"] == 1


def test_review_queue_roundtrip_and_dedupe():
    with tempfile.TemporaryDirectory() as t:
        path = Path(t) / "q.jsonl"
        a = rq.add_item("candidate", {"x": 1}, path, dedupe_key="k")
        assert rq.add_item("candidate", {"x": 1}, path, dedupe_key="k") == a
        assert rq.list_items(path, "pending").shape[0] == 1
        rq.decide(a, "approved", "ok", path)
        assert rq.list_items(path, "approved").shape[0] == 1 and rq.list_items(path, "pending").empty


def test_basket_matrix_levels():
    d = _lines()
    d["category"] = "c"; d["brand"] = None; d["function"] = "f"; d["department"] = "d"; d["owner"] = None
    bm = build_basket_matrix(d, "category")
    assert bm.X.shape[1] == 1
