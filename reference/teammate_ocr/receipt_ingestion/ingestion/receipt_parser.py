"""Retailer-independent rules; ambiguous OCR remains evidence, never guessed data."""
import re
from datetime import date, time
from .models import Entry, Receipt
from .ocr import OCRLine

MONEY = r"-?\d+[.,]\d{2}"
END_AMOUNT = re.compile(rf"(?:[£$€]\s*)?({MONEY})\s*(?:[A-Z*])?\s*$")
DETAIL = re.compile(rf"(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|g|lb|l)?\s*(?:[x×@]|at)\s*[£$€]?\s*(?P<price>{MONEY})(?:\s*/\s*(?:kg|g|lb|l))?", re.I)
THREE_COLUMNS = re.compile(rf"^(?P<name>.+?)\s+(?P<qty>\d+)\s+(?P<price>{MONEY})\s+(?P<total>{MONEY})$")
TOTAL = re.compile(r"^(?:(?:grand|receipt|transaction)\s+total|total(?:\s+(?:due|to pay))?|amount\s+due|balance\s+due)\b", re.I)
PAYMENT = re.compile(r"^(?:card|cash|visa|mastercard|amex|debit|credit|tender|change|payment|paid|contactless)\b", re.I)
META = re.compile(r"^(?:tel|phone|www\.|https?://|vat\s*(?:no|number|reg)|cashier|operator|till|terminal|transaction\s*(?:id|no)|receipt\s*(?:id|no)|loyalty|clubcard|nectar|points|auth|approval|account|a/c)\b", re.I)
FOOTER = re.compile(r"^(?:thank\s*you|thanks|please|visit|survey|opening|you\s+saved|total\s+savings|items?\s*(?:sold|count|:)|\d+\s+items?\b)", re.I)


def number(text):
    return float(text.replace(",", "."))


def entry(kind, description, amount=None, quantity=None, unit_price=None,
          affects_total=None, uncertainty=None):
    return Entry(kind=kind, description=description, amount=amount, quantity=quantity,
                 unit_price=unit_price, promotion=None, affects_total=affects_total,
                 uncertainty=uncertainty)


def parse_lines(lines: list[OCRLine]) -> Receipt:
    receipt = Receipt(store_name=None, store_address=None, date=None, time=None,
                      currency=None, total=None, entries=[], uncertainty=[],
                      raw_ocr_text="\n".join(f"[page {l.page}, OCR {l.confidence:.2f}] {l.text}" for l in lines))
    receipt.uncertainty.append("Local OCR and heuristic parsing require review against the image.")
    totals, dates, times = set(), set(), set()
    previous_index, previous_page = -2, None
    total_seen = False
    active_item = None
    summary = False
    header_open = True
    receipt.priced_line_count = 0
    for index, line in enumerate(lines):
        text = re.sub(r"\s+", " ", line.text).strip()
        if not text:
            continue
        if line.confidence < 0.75:
            if re.match(r"^\d+\s+", text) and END_AMOUNT.search(text):
                receipt.priced_line_count += 1
            active_item = None
            receipt.entries.append(entry("other", text, uncertainty="Low OCR confidence; transcribe and classify manually"))
            continue
        # Insert only a parsing separator between a fully delimited ISO date and
        # a clock time. Raw OCR/product text remains unchanged.
        date_text = re.sub(r"(\d{4}-\d{2}-\d{2})(?=\d{1,2}:\d{2})", r"\1 ", text)
        for symbol, currency in [("£", "GBP"), ("€", "EUR")]:
            if symbol in text or re.search(rf"\b{currency}\b", text):
                if receipt.currency and receipt.currency != currency:
                    receipt.uncertainty.append("Multiple currencies detected; check currency")
                receipt.currency = currency
        date_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", date_text)
        local_date = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4}|\d{2})\b", date_text)
        time_match = re.search(r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b", date_text)
        if date_match or local_date or time_match:
            header_open = False
            active_item = None
            try:
                if date_match:
                    dates.add(date(*map(int, date_match.groups())))
                elif local_date:
                    a, b, year = map(int, local_date.groups())
                    if year < 100 or (a <= 12 and b <= 12 and a != b):
                        receipt.uncertainty.append(f"Ambiguous date: {local_date.group()}; enter YYYY-MM-DD")
                    elif a > 12 or a == b:
                        dates.add(date(year, b, a))
                    else:
                        dates.add(date(year, a, b))
                if time_match:
                    hour, minute, second = time_match.groups()
                    if re.search(r"\b[AP]M\b", text, re.I):
                        receipt.uncertainty.append(f"12-hour time needs review: {time_match.group()}")
                    else:
                        times.add(time(int(hour), int(minute), int(second or 0)))
            except ValueError:
                receipt.uncertainty.append(f"Invalid date/time OCR: {text}")
            continue
        amount_match = END_AMOUNT.search(text)
        amount = number(amount_match[1]) if amount_match else None
        description = text[:amount_match.start()].strip() if amount_match else text
        compact = re.sub(r"\s+", "", description).upper()
        if re.search(r"\b(?:reprinted|printed)\s+receipt\b", text, re.I):
            header_open = False
            active_item = None
            continue
        loyalty_adjustment = amount is not None and re.search(r"\b(?:clubcard|nectar|loyalty)\s+(?:price|saving|discount|offer)\b", description, re.I)
        if FOOTER.search(text) or re.match(r"^any questions\b", text, re.I) or (META.search(text) and not loyalty_adjustment):
            active_item = None
            continue
        if TOTAL.search(text) or compact in {"TOTAL", "GRANDTOTAL", "AMOUNTDUE", "TOTALDUE", "BALANCEDUE"}:
            active_item = None
            if amount is not None:
                totals.add(amount)
            else:
                receipt.uncertainty.append(f"Unreadable receipt total: {text}")
            total_seen = True
            continue
        kind, affects, note = None, None, None
        if re.match(r"^(?:sub\s*total)\b", text, re.I):
            kind, affects = "subtotal", False
            summary = True
        elif re.match(r"^(?:savings|promotions)\s*:", text, re.I):
            kind, affects = "discount", False
        elif PAYMENT.search(text):
            kind, affects = "payment", False
        elif re.match(r"^(?:vat|tax|gst)\b", text, re.I) or compact in {"VATINCLUDED", "TAXINCLUDED", "GSTINCLUDED", "INCLUDEDVAT"}:
            kind = "tax"
            affects = False if re.search(r"incl", text, re.I) else None
            note = None if affects is False else "Confirm whether tax is included or added separately"
        elif loyalty_adjustment or re.search(r"\b(?:coupon|discount|saving|offer|promo)\b", description, re.I) or compact.endswith(("COUPON", "DISCOUNT", "SAVING", "SAVINGS")):
            kind = "discount"
            affects = True if amount is not None and amount < 0 else None
            note = "Confirm discount is not already included in product prices"
        if kind:
            if (kind == "discount" and not summary and active_item is not None
                    and amount is not None and amount < 0
                    and re.match(r"^(?:special offer|item discount)\b", description, re.I)):
                active_item.promotion = description
                active_item.promotion_amount = round((active_item.promotion_amount or 0) + amount, 2)
                active_item.amount = round(active_item.amount + amount, 2)
                affects = False
            parsed = entry(kind, description, amount, affects_total=affects, uncertainty=note)
            if kind == "discount":
                parsed.promotion = description
            receipt.entries.append(parsed)
            if kind == "discount" and affects is False:
                parsed.uncertainty = None
            active_item = None
            continue
        if total_seen:
            if amount is not None:
                receipt.entries.append(entry("other", text, uncertainty="Unclassified line after total; review"))
            continue
        detail, columns = DETAIL.search(text), THREE_COLUMNS.match(text)
        if detail:
            active_item = None
            name = text[:detail.start()].strip()
            remainder = text[detail.end():].strip()
            detail_total = END_AMOUNT.fullmatch(remainder)
            total = number(detail_total[1]) if detail_total else None
            qty, price = number(detail["qty"]), number(detail["price"])
            unit_note = f"Quantity unit: {detail['unit']}" if detail["unit"] else None
            adjacent = previous_index == index-1 and previous_page == line.page
            if not name and adjacent and receipt.entries and receipt.entries[-1].kind in {"other", "product"}:
                previous = receipt.entries[-1]
                if previous.quantity is None:
                    if previous.kind == "other" and total is not None:
                        receipt.priced_line_count += 1
                    unit_note = ((unit_note + "; ") if unit_note else "") + "Quantity detail linked to preceding row; verify association"
                    previous.kind, previous.quantity, previous.unit_price = "product", qty, price
                    previous.affects_total = True
                    if total is not None:
                        if previous.amount is not None and previous.amount != total:
                            unit_note = (unit_note or "") + " Conflicting adjacent line totals; review"
                        else:
                            previous.amount = total
                    previous.uncertainty = unit_note
                else:
                    receipt.entries.append(entry("other", text, uncertainty="Unmatched quantity detail"))
            elif name:
                if total is not None:
                    receipt.priced_line_count += 1
                receipt.entries.append(entry("product", name, total, qty, price, True, unit_note))
            else:
                receipt.entries.append(entry("other", text, uncertainty="Quantity detail has no adjacent product"))
            previous_index, previous_page = index, line.page
            continue
        if columns:
            active_item = None
            receipt.priced_line_count += 1
            receipt.entries.append(entry("product", columns["name"], number(columns["total"]),
                                         number(columns["qty"]), number(columns["price"]), True))
        elif amount is not None and amount < 0:
            active_item = None
            receipt.entries.append(entry("other", description, amount, uncertainty="Negative unclassified amount: return, void or discount; review"))
        elif amount is not None and re.search(r"[A-Za-z]", description):
            receipt.priced_line_count += 1
            header_open = False
            leading = re.fullmatch(r"(\d+)\s+([A-Za-z].*)", description)
            if leading:
                quantity = int(leading[1])
                active_item = entry("product", leading[2], round(quantity*amount, 2),
                                    quantity, amount, True)
                receipt.entries.append(active_item)
            else:
                active_item = None
                receipt.entries.append(entry("product", description, amount, affects_total=True,
                                             uncertainty="Quantity and unit price not explicitly printed"))
        elif amount is not None and not description and previous_index == index-1 and previous_page == line.page and receipt.entries and receipt.entries[-1].kind == "other":
            active_item = None
            receipt.priced_line_count += 1
            receipt.entries[-1].kind = "product"
            receipt.entries[-1].amount = amount
            receipt.entries[-1].affects_total = True
            receipt.entries[-1].uncertainty = "Price-only continuation; verify association; quantity/unit price unknown"
        elif receipt.store_name is None and header_open and re.search(r"[A-Za-z]", text):
            receipt.store_name = text.title() if text.isupper() else text
            receipt.uncertainty.append("Merchant taken from receipt header; verify")
        elif header_open and (re.search(r"\b(?:street|road|avenue|lane|way|drive|st\.|rd\.)\b", text, re.I) or re.match(r"^\d+.*(?:street|road|avenue|lane|drive)$", text, re.I)) and not receipt.entries:
            receipt.store_address = text
        elif header_open and re.fullmatch(r"[A-Za-z][A-Za-z '\-]+", text) and re.search(r"\b(?:express|superstore|extra|local|market)\b$", text, re.I):
            receipt.store_name += " " + text
            # Some receipts print only a branch location, without a postal
            # address. Preserve that evidence rather than dropping it.
            if receipt.store_address is None:
                receipt.store_address = text
                receipt.uncertainty.append("Store address contains the printed branch location only; full postal address not provided.")
        elif re.fullmatch(r"[\s=*_\-]+", text) or re.match(r"^(?:description|item|qty|quantity|price)\b", text, re.I):
            active_item = None
            continue
        elif active_item is not None and previous_page == line.page and amount is None and not re.match(r"^\d+\s+[A-Za-z]", text):
            active_item.description += " " + text
        else:
            if amount is not None and not description:
                receipt.priced_line_count += 1
            active_item = None
            receipt.entries.append(entry("other", text, uncertainty="Unpriced/unclassified text; classify as product if appropriate"))
        previous_index, previous_page = index, line.page
    for field, values in [("date", dates), ("time", times), ("total", totals)]:
        if len(values) == 1:
            setattr(receipt, field, values.pop())
        elif len(values) > 1:
            receipt.uncertainty.append(f"Conflicting {field} values; possible multiple receipts. Split uploads or review manually.")
    if not lines:
        receipt.uncertainty.append("No text detected. Try a sharper, upright, well-lit image or enter rows manually.")
    return receipt
