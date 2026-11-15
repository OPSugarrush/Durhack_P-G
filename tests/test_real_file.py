"""Fixtures for THIS workbook only. Skipped when the file is absent. Never copy these numbers into src/."""
from pathlib import Path
import pytest

from needstate.config import ROOT, load_config

CONFIG = ROOT / "configs/pipeline.yaml"
DATA = load_config(CONFIG).input_path
if not DATA.exists() and DATA.with_name(DATA.name.replace("_", " ")).exists():
    DATA = DATA.with_name(DATA.name.replace("_", " "))
pytestmark = pytest.mark.skipif(not DATA.exists(), reason="Supplied workbook is not available in this checkout")


def test_workbook_ingests_and_resolves():
    if not DATA.exists():
        return
    from needstate.pipeline import process_lines
    from needstate.ingestion.adapters import load_lines
    cfg = load_config(CONFIG)

    r = process_lines(load_lines(DATA, cfg.mapping), cfg)
    a = r.audit
    assert (a["n_lines"], a["n_receipts"], a["n_consumers"]) == (32776, 3005, 300)
    assert a["line_total_mismatches"] == 0 and a["receipt_total_mismatches"] == 0
    assert len(r.resolution.catalogue) < 108          # truncation/abbreviation duplicates collapsed
    assert r.lines["family_id"].notna().all()
    assert r.lines["promotion_flag"].isna().mean() > 0.8   # null promotion = unknown, not False


def test_workbook_expected_findings():
    if not DATA.exists():
        return
    from needstate.pipeline import process_lines
    from needstate.ingestion.adapters import load_lines
    cfg = load_config(CONFIG)
    from needstate.baskets.construction import build_basket_matrix
    from needstate.patterns.routines import concentration
    from needstate.patterns.trends import trend_scan
    bm = build_basket_matrix(process_lines(load_lines(DATA, cfg.mapping), cfg).lines)
    _, summary = concentration(bm)
    trends = trend_scan(bm)
    assert summary["concentration_ratio"] > 3
    assert int(trends["significant"].sum()) <= 2
    assert trends["seasonality"].iloc[0].startswith("unassessable")
