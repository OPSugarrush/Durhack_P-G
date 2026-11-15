from datetime import date
from pathlib import Path
import socket
import pytest
from ingestion.ocr import OCRLine, group_rows
from ingestion.receipt_parser import parse_lines
from ingestion.extraction import extract_receipt
from ingestion.images import prepare_images


def parse(text):
    return parse_lines([OCRLine(line) for line in text.splitlines()])


def products(receipt):
    return [e for e in receipt.entries if e.kind == 'product']


def test_simple_items_never_infer_quantity():
    r = parse('Town Grocer\n14/11/2026\nMILK 1L 1.50\nBREAD 2.00\nTOTAL 3.50\nCASH 5.00\nCHANGE 1.50')
    assert r.store_name == 'Town Grocer' and r.date == date(2026,11,14)
    assert len(products(r)) == 2
    assert products(r)[0].quantity is None and products(r)[0].unit_price is None
    assert r.total == 3.5


@pytest.mark.parametrize('line,qty,price,total', [
    ('MILK 2 x 1.50 3.00', 2, 1.5, 3),
    ('APPLES 0.750 kg @ 2.00/kg 1.50', .75, 2, 1.5),
    ('BREAD 2 1.25 2.50', 2, 1.25, 2.5),
    ('MILK 2 @ 1,50 3,00', 2, 1.5, 3),
])
def test_explicit_quantities(line, qty, price, total):
    p = products(parse('Market\n'+line))[0]
    assert (p.quantity,p.unit_price,p.amount) == (qty,price,total)


def test_continuation_without_total_preserves_printed_amount():
    p = products(parse('Market\nBEANS 3.00\n2 x 1.50'))[0]
    assert (p.quantity,p.unit_price,p.amount) == (2,1.5,3)


def test_low_confidence_not_committed_as_prices():
    r = parse_lines([OCRLine('Market'), OCRLine('MILK 8.00', .4), OCRLine('TOTAL 8.00')])
    assert not products(r)
    assert r.entries[0].amount is None
    assert 'Low OCR' in r.entries[0].uncertainty


def test_ambiguous_date_and_conflicting_totals():
    r = parse('Market\n03/04/2026\nBREAD 2.00\nTOTAL 2.00\nTOTAL 3.00')
    assert r.date is None and r.total is None
    assert any('Ambiguous date' in i for i in r.uncertainty)


def test_no_text():
    assert not products(parse_lines([]))
    assert any('No text' in i for i in parse_lines([]).uncertainty)


def test_branch_location_is_preserved_as_partial_address():
    r = parse('TESCO\nDurham Claypath Express\nAny questions please visit\nwww.tesco.com/store-locator\n14/11/2026\nBREAD 2.00')
    assert r.store_name == 'Tesco Durham Claypath Express'
    assert r.store_address == 'Durham Claypath Express'
    assert any('full postal address not provided' in note for note in r.uncertainty)


def test_branch_does_not_replace_printed_street_address():
    r = parse('TESCO\n12 High Street\nDurham Claypath Express\n14/11/2026\nBREAD 2.00')
    assert r.store_address == '12 High Street'


def test_missing_location_stays_unknown():
    assert parse('TESCO\n14/11/2026\nBREAD 2.00').store_address is None


def test_loyalty_discount_not_discarded_as_membership_metadata():
    r = parse('Market\nBREAD 2.00\nClubcard price -0.50\nTOTAL 1.50')
    discount = [e for e in r.entries if e.kind == 'discount'][0]
    assert discount.amount == -.5 and discount.promotion == 'Clubcard price'


def test_row_grouping():
    rows = group_rows([
        ([[200,10],[250,10],[250,30],[200,30]], '1.50', .99),
        ([[10,11],[100,11],[100,31],[10,31]], 'MILK', .95),
        ([[10,50],[100,50],[100,70],[10,70]], 'BREAD', .9),
    ])
    assert rows[0].text == 'MILK  1.50'
    assert rows[0].confidence == .95 and len(rows) == 2


def test_real_ocr_offline(monkeypatch):
    # Includes first engine initialization: model downloads/network would fail.
    def deny_network(*args, **kwargs):
        raise AssertionError('OCR must work without network')
    monkeypatch.setattr(socket.socket, 'connect', deny_network)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    path = Path(__file__).parents[1]/'examples/demo_receipt.png'
    r = extract_receipt(prepare_images(path.read_bytes(), path.name))
    assert r.store_name and 'EXAMPLE' in r.store_name.upper()
    assert r.total == 5.5
    assert len(products(r)) == 2
    assert products(r)[0].amount == 4
    assert products(r)[1].quantity == .5
    assert r.date == date(2026,11,14) and r.time.hour == 10
    assert any(e.kind == 'discount' and e.amount == -.5 for e in r.entries)
    assert any(e.kind == 'tax' and e.affects_total is False for e in r.entries)


def test_joined_ocr_words_and_datetime():
    r = parse('Market\n2026-11-1410:30\nMILK 2.00\nBASKETCOUPON -0.50\nGRANDTOTAL 1.50\nVATINCLUDED 0.10')
    assert r.date == date(2026,11,14) and r.time.hour == 10
    assert len(products(r)) == 1 and r.total == 1.5


def test_unclassified_negative_amount_requires_review():
    r = parse('Market\nVOIDED BREAD -2.00')
    assert not products(r)
    assert r.entries[0].kind == 'other' and r.entries[0].affects_total is None
