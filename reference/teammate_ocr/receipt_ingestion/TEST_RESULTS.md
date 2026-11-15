# Validation results — local OCR MVP

Executed on 14 November 2026 with the project's new isolated `.venv`, Python 3.12
(x64) on Windows. No scratch dependency folder or OpenAI installation was used.

- `.venv\Scripts\python.exe -m pytest -q`: **34 passed in 6.29 seconds**.
- `.venv\Scripts\python.exe -m pip check`: **No broken requirements found**.
- Streamlit started from the project environment with OPENAI_API_KEY and PYTHONPATH
  removed. `http://127.0.0.1:8519/_stcore/health` returned **HTTP 200 / ok**.
  The temporary smoke-test server was stopped afterward.
- Confirmed `importlib.util.find_spec('openai')` is None in the environment.

The actual OCR integration test initializes package-bundled ONNX models and reads
`examples/demo_receipt.png` while socket connections are blocked and the API key is
unset. It verifies two product rows, the first line total, the weighted second
quantity, grand total, merchant, date/time, coupon classification and included VAT.
This is real local OCR, not a mocked OCR response.

Other tests cover single-line items with unknown quantities, explicit quantity and
price columns, weighted purchases, quantity continuations, comma decimals, missing
spaces in OCR, ambiguous dates, conflicting totals, low-confidence rows, loyalty
adjustments, unidentified negative amounts, geometric row grouping, blank OCR,
invalid Pydantic data, original fixture compatibility, mocked-reader pipeline,
PDF rendering/limits, Excel native types and column ordering, JSON provenance,
manual edits, formula-safe export, UUIDs, arithmetic and the Streamlit demo.

The first real OCR run revealed missing-space errors: BASKETCOUPON was classified
as a product, and joined ISO date/time text was missed. Parser handling was fixed
and regression tests added. The final full run above includes those fixes.

Key versions: rapidocr_onnxruntime 1.4.4, onnxruntime 1.32.0, OpenCV 5.0.0.93,
Streamlit 1.67.0, Pydantic 2.14.3, pandas 3.1.1, openpyxl 3.1.5,
pypdfium2 5.15.2, pytest 9.2.0. The OCR models are loaded from installed package
files, not downloaded at runtime. Full installed versions are in requirements-lock.txt.

Limitations: the supplied project contains no real supermarket photographs. These
results demonstrate offline execution and fixture correctness, not field accuracy
across retailers. OCR can omit spaces or misread faint text; heuristic parsing can
misclassify unfamiliar formats. Review the image and uncertainty flags before export.
The Streamlit workflow was tested via AppTest and a server health check, not a manual
browser interaction. The offline demo remains available without initializing OCR.
