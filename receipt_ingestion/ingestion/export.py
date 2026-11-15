import hashlib
import io
import json
from pathlib import Path
from uuid import uuid4
import pandas as pd
from openpyxl import Workbook
from .models import Receipt
from .validation import check_receipt

SCHEMA = json.loads(Path(__file__).with_name("schema.json").read_text())
COLUMNS = [c[0] for c in SCHEMA["columns"]]


def new_id(prefix):
    return f"{prefix}-{uuid4()}"


def rows(receipt: Receipt, consumer_id: str, receipt_id: str, filename: str):
    if not consumer_id.strip() or not receipt_id.strip():
        raise ValueError("Consumer and receipt IDs are required")
    result = []
    for number, entry in enumerate((e for e in receipt.entries if e.kind == "product"), 1):
        values = receipt.model_dump() | entry.model_dump() | dict(
            consumer_id=consumer_id.strip(), receipt_id=receipt_id, filename=filename,
            line_number=number)
        values["promotion"] = entry.promotion_amount
        result.append({column: values[field] for column, field, _ in SCHEMA["columns"]})
    return result


def dataframe(receipt, consumer_id, receipt_id, filename):
    frame = pd.DataFrame(rows(receipt, consumer_id, receipt_id, filename), columns=COLUMNS)
    for name, _, dtype in SCHEMA["columns"]:
        if dtype in {"number", "integer"}:
            frame[name] = frame[name].astype("Int64" if dtype == "integer" else "Float64")
    return frame


def excel_bytes(receipt, consumer_id, receipt_id, filename):
    book = Workbook()
    sheet = book.active
    sheet.title = SCHEMA["sheet"]
    sheet.append(COLUMNS)
    for record in rows(receipt, consumer_id, receipt_id, filename):
        sheet.append(list(record.values()))
        for cell, (_, _, dtype) in zip(sheet[sheet.max_row], SCHEMA["columns"]):
            if dtype == "text" and cell.value is not None:
                cell.data_type = "s"  # Never execute receipt text as Excel formulas.
            if dtype == "date":
                cell.number_format = "yyyy-mm-dd"
            elif dtype == "time":
                cell.number_format = "h:mm"
            elif cell.column in (9, 10, 11, 12):
                cell.number_format = "#,##0.00"
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


def json_bytes(receipt, consumer_id, receipt_id, filename, original=None, source_hash=None):
    records = rows(receipt, consumer_id, receipt_id, filename)
    def stable_id(prefix, value):
        return prefix + hashlib.sha256(value.encode()).hexdigest()[:24] if value else None
    retailer_id = stable_id("ret-", receipt.store_name)
    timestamp = (f"{receipt.date.isoformat()}T{receipt.time.isoformat()}"
                 if receipt.date and receipt.time else None)
    canonical = {
        "transaction_id": receipt_id, "customer_id": consumer_id,
        "retailer_id": retailer_id,
        "store_id": stable_id("store-", (receipt.store_name or "") + "|" + receipt.store_address)
                    if receipt.store_address and receipt.store_name else None,
        "timestamp": timestamp,
        "line_items": [{"line_id": f"{receipt_id}:{r['Line Number']}",
                        "transaction_id": receipt_id, "raw_product_text": r["Product Name"],
                        "canonical_product_id": None, "quantity": r["Quantity"],
                        "unit_price": r["Unit Price"], "line_total": r["Line Total"],
                        "promotion_flag": True if r["Promotion"] else None,
                        "line_number": r["Line Number"]} for r in records],
    }
    payload = {"schema_version": "needstate.receipt.v1", "rows": records,
               "transaction": canonical, "receipt": receipt.model_dump(mode="json"),
               "original_extraction": (original or receipt).model_dump(mode="json"),
               "source": {"filename": filename, "sha256": source_hash},
               "validation_issues": check_receipt(receipt),
               "human_edited": original is not None and original != receipt}
    return json.dumps(payload, default=lambda v: v.isoformat(), ensure_ascii=False,
                      allow_nan=False, indent=2).encode("utf-8")
