import io
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from PIL import Image
from openpyxl import load_workbook
from ingestion.models import Receipt
from ingestion.images import prepare_images
from ingestion.extraction import extract_receipt
from ingestion.export import COLUMNS, rows, excel_bytes, json_bytes, new_id
from ingestion.validation import check_receipt
from ingestion.parsing import edited_receipt
import pandas as pd


@pytest.fixture
def receipt():
    return Receipt.model_validate_json((Path(__file__).parents[1]/"examples/receipt.json").read_text())


def test_mocked_end_to_end(receipt):
    image = (Path(__file__).parents[1]/"examples/demo_receipt.png").read_bytes()
    from ingestion.ocr import OCRLine
    text = ['Example Market', '12 Example Street', '2026-11-14 10:30',
            'OAT DRINK 1L', '2 x 2.00 4.00', 'APPLES KG', '0.500 kg @ 4.00/kg 2.00',
            'BASKET COUPON -0.50', 'TOTAL GBP 5.50', 'VAT INCLUDED 0.20', 'CARD 5.50']
    reader = Mock(return_value=[OCRLine(t) for t in text])
    extracted = extract_receipt(prepare_images(image, "receipt.png"), reader)
    args = extracted, "C-test", "R-test", "receipt.png"
    book = load_workbook(io.BytesIO(excel_bytes(*args)))
    sheet = book.active
    assert sheet.title == "Synthetic Receipts"
    assert [c.value for c in sheet[1]] == COLUMNS
    assert sheet.max_row == 3  # no tax, coupon or payment product rows
    assert sheet["F2"].data_type == "d" and sheet["M2"].data_type == "d"
    assert sheet["H3"].value == 0.5 and sheet["I2"].data_type == "n"
    payload = json.loads(json_bytes(*args))
    assert len(payload["transaction"]["line_items"]) == 2
    assert len(payload["receipt"]["entries"]) == 5
    assert not any("mismatch" in i for i in check_receipt(extracted))
    reader.assert_called_once()
    assert 'OAT DRINK' in extracted.raw_ocr_text


def test_missing_and_ambiguous(receipt):
    receipt.entries[0].quantity = None
    receipt.entries[0].amount = None
    receipt.date = None
    receipt.entries[2].affects_total = None
    issues = check_receipt(receipt)
    assert any("unverifiable" in i for i in issues)
    assert rows(receipt, "C", "R", "x")[0]["Quantity"] is None
    payload = json.loads(json_bytes(receipt, "C", "R", "x"))
    assert payload["transaction"]["timestamp"] is None
    assert payload["transaction"]["line_items"][1]["promotion_flag"] is None


def test_mismatch(receipt):
    receipt.total = 100
    receipt.entries[0].amount = 50
    issues = check_receipt(receipt)
    assert any("quantity ×" in i for i in issues)
    assert any("total mismatch" in i for i in issues)


def test_empty_input():
    with pytest.raises(ValueError):
        extract_receipt([])


def test_edits_and_formula_safety(receipt):
    table = pd.DataFrame([e.model_dump() for e in receipt.entries])
    table.loc[0, "description"] = '=HYPERLINK("https://example.com")'
    revised = edited_receipt(receipt, {"total": 6}, table)
    book = load_workbook(io.BytesIO(excel_bytes(revised, "=1+1", "R", "x")))
    assert book.active["G2"].data_type == "s"
    assert book.active["A2"].data_type == "s"
    payload = json.loads(json_bytes(revised, "C", "R", "x", original=receipt))
    assert payload["human_edited"] and payload["original_extraction"]["total"] == 5.5


@pytest.mark.parametrize("data,name", [(b"", "x.png"), (b"fake", "x.pdf"), (b"x", "x.exe")])
def test_invalid_uploads(data, name):
    with pytest.raises(ValueError):
        prepare_images(data, name)


def test_nonfinite_rejected(receipt):
    data = receipt.model_dump()
    data["total"] = float("nan")
    with pytest.raises(ValueError):
        Receipt.model_validate(data)


def test_ids_unique():
    assert new_id("R") != new_id("R")


def test_pdf():
    import pypdfium2 as pdfium
    document = pdfium.PdfDocument.new()
    page = document.new_page(300, 600)
    page.close()
    buffer = io.BytesIO()
    document.save(buffer)
    document.close()
    assert len(prepare_images(buffer.getvalue(), "receipt.pdf")) == 1


def test_pdf_page_limit():
    import pypdfium2 as pdfium
    document = pdfium.PdfDocument.new()
    for _ in range(6):
        document.new_page(100, 100).close()
    buffer = io.BytesIO()
    document.save(buffer)
    document.close()
    with pytest.raises(ValueError, match="1 to 5"):
        prepare_images(buffer.getvalue(), "long.pdf")


def test_ocr_error_propagates():
    reader = Mock(side_effect=RuntimeError("OCR model unavailable"))
    with pytest.raises(RuntimeError):
        extract_receipt(["data:image/jpeg;base64,eA=="], reader)


def test_unknown_vs_zero(receipt):
    receipt.entries[0].unit_price = 0
    receipt.entries[0].amount = 0
    receipt.total = 1.5
    assert not any("mismatch" in i for i in check_receipt(receipt))
    assert rows(receipt, "C", "R", "x")[0]["Unit Price"] == 0


def test_additive_tax_and_included_discount(receipt):
    receipt.entries[2].affects_total = False
    receipt.entries[3].affects_total = True
    receipt.total = 6.2
    assert not any("mismatch" in i for i in check_receipt(receipt))


def test_empty_receipt(receipt):
    receipt.entries = []
    assert "No purchased products identified" in check_receipt(receipt)
    assert rows(receipt, "C", "R", "x") == []
