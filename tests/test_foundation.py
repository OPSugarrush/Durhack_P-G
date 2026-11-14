import numpy as np
import pandas as pd
import pytest

from needstate.config import load_config
from needstate.ingestion.adapters import to_canonical
from needstate.patterns.cooccurrence import curveball_trade, null_model_pairs
from needstate.baskets.construction import build_basket_matrix
from needstate.pipeline import process_lines
from tests.helpers import mini_lines, synthetic_bm


def test_curveball_preserves_binary_margins():
    rng = np.random.default_rng(14)
    original = (rng.random((12, 20)) < .3).astype(int)
    rows = [set(np.flatnonzero(r)) for r in original]
    for _ in range(1000):
        curveball_trade(rows, rng)
    rebuilt = np.zeros_like(original)
    for i, row in enumerate(rows):
        rebuilt[i, list(row)] = 1
    assert np.array_equal(original.sum(0), rebuilt.sum(0))
    assert np.array_equal(original.sum(1), rebuilt.sum(1))


def test_singleton_consumer_blocks_cannot_create_evidence():
    bm = synthetic_bm(n_consumers=20, receipts_per=1, n_products=8)
    out = null_model_pairs(bm, n_perm=9, min_count=1)
    assert (out.p_perm == 1).all()
    assert np.allclose(out['count'], out.null_mean)


def test_missing_names_reduce_quality_without_removing_observed_lines():
    cfg = load_config()
    clean = mini_lines()
    bad = clean.copy()
    bad.loc[0, 'raw_product_text'] = pd.NA
    result = process_lines(bad, cfg)
    assert len(result.lines) == len(clean)
    assert pd.isna(result.lines.loc[0, 'family_id'])
    assert result.quality.loc['T0', 'data_completeness'] < 1


def test_two_source_schemas_produce_same_canonical_records():
    a = pd.DataFrame({'receipt':['a'], 'date':['2026-01-01'], 'text':['Bread'], 'price':['2.50']})
    b = a.rename(columns={'receipt':'order', 'date':'at', 'text':'description', 'price':'unit'})
    ca = to_canonical(a, {'fields':{'transaction_id':'receipt','timestamp':'date','raw_product_text':'text','unit_price':'price'}})
    cb = to_canonical(b, {'fields':{'transaction_id':'order','timestamp':'at','raw_product_text':'description','unit_price':'unit'}})
    pd.testing.assert_frame_equal(ca, cb)


def test_conflicting_receipt_identity_is_rejected():
    df = pd.DataFrame({'id':['a','a'], 'at':['2026-01-01','2026-01-02'], 'text':['X','Y']})
    with pytest.raises(ValueError, match='conflicting timestamp'):
        to_canonical(df, {'fields':{'transaction_id':'id','timestamp':'at','raw_product_text':'text'}})
