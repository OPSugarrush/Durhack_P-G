"""Frozen source header contract, independent of the runtime mapping file."""
from ingestion.export import COLUMNS
from ingestion.models import Receipt
from ingestion.receipt_parser import parse_lines
from ingestion.ocr import OCRLine
import pytest


def test_exact_source_header_contract():
    assert COLUMNS == [
        "Consumer ID", "Receipt ID", "Image Filename", "Store Name", "Store Address",
        "Date", "Product Name", "Quantity", "Unit Price", "Promotion", "Line Total",
        "Total Spend", "Time", "Line Number",
    ]


def test_schema_rejects_invalid_date_and_extra_fields():
    data = parse_lines([OCRLine('Market')]).model_dump()
    data['date'] = '2026-02-31'
    with pytest.raises(ValueError):
        Receipt.model_validate(data)
    data['date'] = None
    data['invented_total'] = 100
    with pytest.raises(ValueError):
        Receipt.model_validate(data)


def test_raw_evidence_is_additive_and_old_fixture_still_valid():
    from pathlib import Path
    receipt = Receipt.model_validate_json((Path(__file__).parents[1]/'examples/receipt.json').read_text())
    assert receipt.raw_ocr_text is None
