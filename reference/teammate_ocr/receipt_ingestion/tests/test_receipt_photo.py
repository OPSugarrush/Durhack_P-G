import io
from datetime import datetime, time
from pathlib import Path

from openpyxl import load_workbook

from ingestion.export import excel_bytes
from ingestion.extraction import extract_receipt
from ingestion.images import prepare_images
from ingestion.validation import check_receipt


def test_tesco_photo_to_excel():
    photo = Path(__file__).parents[1] / "examples" / "test1.jpg"
    receipt = extract_receipt(prepare_images(photo.read_bytes(), photo.name))
    book = load_workbook(io.BytesIO(excel_bytes(receipt, "consumer", "receipt", photo.name)))
    rows = list(book["Synthetic Receipts"].values)[1:]
    assert len(rows) == receipt.priced_line_count == 7
    names = [
        "Halls Soothers Blackcurrant Sweets With Liquid Centres 45g",
        "Tesco Panini 2 Pack",
        "Always Ultra Secure Night Size 4 Sanitary Towels With Wings 8 Pack",
        "Strepsils Honey & Lemon Lozenges X36 For Sore Throat",
        "Monster Energy Drink Mango Loco 500ml",
        "Pampers Sensitive Baby Wipes Plastic Free 52 Pack",
        "Head And Shoulders 2 In 1 Classic Clean Shampoo 250ml",
    ]
    prices = [0.90, 1.10, 2.25, 6.50, 2.45, 1.15, 3.10]
    for index, (row, name, price) in enumerate(zip(rows, names, prices), 1):
        assert row[:6] == ("consumer", "receipt", photo.name, "Tesco Durham Claypath Express",
                           "Durham Claypath Express", datetime(2026, 11, 14))
        assert row[6].replace("C1ean", "Clean").replace("m1", "ml") == name
        adjustment, net = (-.73, .37) if index == 2 else (None, price)
        assert row[7:] == (1, price, adjustment, net, 16.72, time(19, 29), index)
    assert not any("difference" in issue for issue in check_receipt(receipt))
    receipt.entries = [entry for entry in receipt.entries if entry.description != names[0]]
    warnings = check_receipt(receipt)
    assert any("difference -0.90" in issue for issue in warnings)
    assert any("7 detected priced lines, 6 product rows" in issue for issue in warnings)
