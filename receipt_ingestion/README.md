# NeedState receipt ingestion — local OCR MVP

This application runs receipt OCR and parsing on your computer. **No OpenAI account,
API key, paid service, Tesseract executable or GPU is required.** Package installation
needs internet access once; receipt extraction and the demo work offline afterward.

## Windows PowerShell setup

Use 64-bit Python 3.12 (recommended). Install it from python.org if `py -3.12 --version`
does not work. A Windows Store alias named `python.exe` is not a usable interpreter.
In PowerShell, change to the folder containing this README:

```powershell
cd 'C:\path\to\receipt_ingestion'
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Open the localhost URL printed by Streamlit. Ctrl+C stops it. Activation is not
required, so these commands avoid PowerShell execution-policy problems entirely.
Alternatively, run `./run.ps1` when your policy permits local scripts.
`requirements-lock.txt` records every version tested on this Windows/Python 3.12
environment; use `-r requirements-lock.txt` instead for an exact-version install.

**On this computer:** a `.venv` has been created in this project using the bundled
Python 3.12 interpreter, and dependencies are installed there. Use its
`.venv\Scripts\python.exe` directly; the old scratch `work/deps` directory is not
required. Virtual environments are machine-specific and are excluded from the ZIP.
If you move the project, recreate the environment with the commands above.

If an existing environment is broken, close Streamlit and rename `.venv` to
`.venv.old` before creating a fresh one. Do not install into a random global Python.
If `py` is unavailable, substitute the full path to your installed Python executable:
`& 'C:\path\to\python.exe' -m venv .venv`. A corporate firewall may require permission
to reach PyPI during installation. DLL load errors in ONNX Runtime on Windows can
require the Microsoft Visual C++ 2015–2022 x64 Redistributable. For ARM Windows, use
an x64 Python under emulation unless all required native packages support ARM64.

## Use

1. Enter or generate a pseudonymous Consumer ID; reuse it for repeat visits.
2. Upload a JPG/JPEG, PNG or PDF of **one receipt**. Maximum: 20 MB, five PDF pages.
3. Click **Extract receipt locally**. The first run loads bundled OCR models.
4. Compare the image and original OCR text with the editable rows. Fix merchant,
   date/time, prices, quantities, row classifications and missing values.
5. Mark only purchased lines as `product`. Correct `affects_total`: true for a
   separately additive amount; false for already-included/informational amounts;
   blank for unknown. Discounts are signed negative amounts.
6. Review the arithmetic warnings, clear resolved uncertainty notes, acknowledge
   review and download Excel and/or JSON.

**Load offline demo** loads the original prefilled synthetic receipt without OCR.
Upload `examples/demo_receipt.png` to exercise the actual local OCR engine instead.
Rows can be added manually even when no text is detected. Unknown entries remain
visible as `other`; they are excluded from product exports until you classify them.
The review always names its source; selecting a new upload does not automatically
replace an existing extraction.

## OCR and parsing design

RapidOCR 1.4.4 (`rapidocr_onnxruntime`) ships detection, orientation and recognition
ONNX models inside its Python package. This MVP pins that version for its packaged
model files and stable CPU API. It is an older standalone distribution, not the
newer RapidOCR API. The app explicitly loads local model paths; it has no download
fallback, API client or remote inference. Streamlit usage telemetry is disabled.

- `ingestion/images.py`: bounded JPG/PNG decoding, EXIF orientation, PDF rendering.
- `ingestion/ocr.py`: local CPU inference and position-based merging of description
  and price boxes into rows. OCR confidence is retained for review.
- `ingestion/receipt_parser.py`: retailer-independent parsing rules.
- `ingestion/extraction.py`: coordinates OCR and parsing (injectable reader in tests).
- `ingestion/models.py`: Pydantic schema, nullable fields, finite-number validation.
- `ingestion/parsing.py`: validates manual edits using the same schema.
- `ingestion/validation.py`: Decimal-based arithmetic checks, 0.02 tolerance.
- `ingestion/schema.json` and `export.py`: exact column mapping and Excel/JSON exports.
- `app.py`: upload, evidence inspection, editable table and downloads.

Parser support includes single-line description/amount pairs, explicit `2 x 1.50`,
`2 @ 1.50`, weighted `0.500 kg @ 4.00/kg`, explicit quantity/unit-price/total columns,
and immediately adjacent quantity-detail lines. Dots or commas are accepted as
printed decimal separators. It does not infer quantity 1, derive unit prices from
line totals, expand names, or use retailer layouts. A pack size in a product name
is not treated as purchased quantity. Digit/letter OCR confusions are not silently
corrected. Raw evidence remains available in JSON and the review interface.

Rows with minimum OCR confidence below 0.75 become unclassified rows with null
numeric fields. This is a review threshold, not a calibrated probability. Ambiguous
numeric dates such as `03/04/2026` remain null; ISO dates and unambiguous day/month
values are accepted. Two-digit years and ambiguous 12-hour times need review.
The merchant is a header candidate, explicitly flagged for confirmation. Missing
addresses remain null. Tax inclusion and discount allocation require review.
Payments, subtotals, tax summaries and coupons are classified separately from products.

## Preserved Excel contract

The supplied workbook has one sheet (`Synthetic Receipts`), 32,776 rows, and the
following 14 columns, preserved in exactly this order:

| Column | Export type |
|---|---|
| Consumer ID | text pseudonym |
| Receipt ID | text UUID |
| Image Filename | text |
| Store Name | text or blank |
| Store Address | text or blank |
| Date | native Excel date or blank |
| Product Name | printed text or blank |
| Quantity | numeric or blank (weights may be fractional) |
| Unit Price | numeric or blank |
| Promotion | negative numeric item adjustment or blank |
| Line Total | numeric or blank |
| Total Spend | numeric or blank, repeated per receipt |
| Time | native Excel time or blank |
| Line Number | sequential product index, starting at 1 |

Unknown values are blank in Excel and null in JSON. No columns are added. The
synthetic workbook's literal `None` promotion strings are not interpreted as proof
of no promotion. Money remains numeric with neutral currency formatting. Receipt
IDs survive edits; a new extraction generates a new ID. Text cells cannot execute
as Excel formulas. Never sum repeated Total Spend values across product rows.

## JSON integration

`needstate.receipt.v1` keeps the existing `rows` and canonical `transaction` objects,
plus complete `receipt`, `original_extraction`, source filename/SHA-256,
`human_edited` and `validation_issues`. The receipt now has an optional additive
`raw_ocr_text` field containing original text, page numbers and OCR scores. This
field is not exported into Excel. Older consumers ignoring extra receipt metadata
remain compatible; strict consumers should permit this additive field.

Canonical IDs, product text and line numbers retain the existing shape. Retailer
and store hashes are local identifiers for downstream master-data resolution.
Canonical product ID remains null: entity resolution belongs to the wider engine.
Timestamp is null unless both date and time are known; no timezone is inferred.
Nullable prices/quantities must be accepted or routed to review downstream.

Excel cannot represent standalone basket adjustments, uncertainty or OCR evidence.
Product totals can therefore differ from Total Spend when a separate coupon exists.
Use JSON's signed adjustments and validation issues for reconciliation. Do not
silently distribute discounts or overwrite printed values to force arithmetic to fit.

## Limits and privacy

Local OCR is less flexible than vision-language extraction. Clean upright English
receipts work best; crumpled paper, logos, unusual layouts, rotation, faint print,
multiple currencies, returns and malformed prices need manual correction. Product
line recognition is heuristic and may miss or misclassify lines. Review the image,
not only the parsed table. A passing arithmetic check does not establish OCR accuracy.
Conflicting dates/totals are flagged; multiple receipts should be uploaded separately.
Two-decimal monetary precision is assumed. Image dimensions and downscaling limits
are implemented in `images.py`; photograph tiny print more closely if necessary.

The app makes no receipt-related network calls and keeps uploads in session memory.
Original OCR text can contain identifiers printed on the receipt, so exported JSON
may contain sensitive evidence even though payment lines are not product rows.
Review before sharing. No database, authentication, catalogue matching, automatic
replenishment inference or production deployment is included.

## Tests

Run `.\.venv\Scripts\python.exe -m pytest -q` from this folder. Tests exercise local
OCR on the synthetic receipt with network connections blocked and no API key;
parser variants; missing/ambiguous fields; row geometry; schema validation;
PDFs; arithmetic; manual edit provenance; Excel/JSON; and Streamlit's demo.
See TEST_RESULTS.md for the actual run results. Synthetic fixtures are regression
checks, not a real supermarket accuracy benchmark. Real receipt photographs were
not supplied with the original spreadsheet and architecture document.

RapidOCR upstream: https://github.com/RapidAI/RapidOCR
## Receipt photo regression

The local OCR engine runs a dark-ink pass to suppress faint reverse print. For
receipts with separate label and price columns, it aligns by order only when the
quantity pattern, footer and box geometry agree. It can reread a visible quantity
glyph in the margin. Other layouts use the normal OCR path.

For the leading-quantity layout, the trailing price is the printed unit price.
Wrapped descriptions join the preceding item, and a following Special Offer or
Item Discount becomes a negative numeric Promotion with a net Line Total.
Savings and Promotions summaries after the subtotal are informational. The
review checks net item totals against the printed total and reports the signed
difference. Separate basket adjustments can explain a difference. Detected
priced rows are also compared with product rows, including after manual edits.

The photo regression uses examples/test1.jpg and permits minor OCR spelling
differences. Keep receipt images private when distributing the project.

