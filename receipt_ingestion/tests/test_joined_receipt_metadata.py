from datetime import date, time
from ingestion.ocr import OCRLine
from ingestion.receipt_parser import parse_lines


def test_joined_us_date_and_explicit_meridiem():
    receipt = parse_lines([OCRLine('Tesco'), OCRLine('Date:11/25/2025Time:10:21AM'),
                           OCRLine('OrganicMilk $5.99'), OCRLine('WholeGrainBread $3.49'),
                           OCRLine('Fresh Bananas $3.98'), OCRLine('Total $14.60')])
    assert receipt.date == date(2025, 11, 25)
    assert receipt.time == time(10, 21)
    assert len([e for e in receipt.entries if e.kind == 'product']) == 3
    assert all(e.quantity is None for e in receipt.entries if e.kind == 'product')


def test_joined_printed_date_and_midnight():
    receipt = parse_lines([OCRLine('PRINTED14/11/2026 12:05AM')])
    assert receipt.date == date(2026, 11, 14)
    assert receipt.time == time(0, 5)
    assert parse_lines([OCRLine('Time:12:05PM')]).time == time(12, 5)
