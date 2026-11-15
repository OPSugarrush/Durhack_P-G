# Receipt uploads and dataset selection

The existing browser application now supports spreadsheet and receipt-photo staging, review, append and temporary focus. Photo extraction imports the teammate's actual modules from `receipt_ingestion/ingestion`, packaged as `needstate_receipt_ingestion`. Its Streamlit app is not run or embedded.

Install with `.venv\Scripts\python.exe -m pip install -e ".[ocr]"` and start with `.venv\Scripts\python.exe -m needstate.webapp --port 8772`. OCR remains optional for spreadsheet users.

## Behavior

- An upload is staged before analysis. Photo rows and metadata can be corrected in the browser, including missing items and row classifications.
- Edited photo rows must be saved before review acceptance. Saving runs the teammate's schema and arithmetic checks again; revision checks prevent accepting stale content from another tab. Existing shopper IDs are suggested for deliberate history matching.
- After a reviewed photo has been analysed, its spreadsheet can be downloaded using the teammate's original Excel exporter and column contract. Changing the saved draft invalidates export readiness until it is reviewed again.
- Add to my data validates and combines canonical receipts, then publishes the new report only after analysis succeeds. Identical receipt IDs/content are skipped; conflicting IDs fail without changing the collection.
- Focus on this upload leaves the collection/report intact. Back to all data restores that report.
- Exact accepted photo hashes cannot be imported again. Matching same-day baskets with different IDs require confirmation; these are candidates, not proven duplicates.
- Single-receipt scopes use the existing product resolver and a descriptive view. They produce no customer trend findings. Missing item prices remain unavailable rather than zero.
- All data, review images and provenance remain in the local server's memory and clear on restart. The example is a separate view, not automatically part of the collection.
- Spreadsheet review allows a currency declaration. Unknown or mixed currencies keep purchase-pattern analysis available but suppress cross-receipt spending comparisons. Single receipts display neutral recorded item amounts, not converted totals.
- Report versions accompany customer-evidence requests to avoid serving another report's indexed finding after a scope change.

## Boundaries

The current edit table covers product descriptions, classification, quantities, prices and item adjustments; original OCR and extraction warnings remain visible. It is not a general spreadsheet editor. There is no persistent database, batch image upload, currency conversion, automatic correction of OCR numbers, or replacement of already-accepted receipts. The matching-basket warning is deliberately conservative and can flag legitimate repeated purchases.

The older synthetic-only `/api/import` endpoint remains for compatibility; the new UI uses staged uploads. Existing multi-receipt analytical rules and evidence limitations remain unchanged. The subsequent [performance review](IMPORT_PERFORMANCE.md) documents faster execution and identical full-report results. Unknown/mixed-currency spending is suppressed in shopper profiles; purchase counts and descriptive category patterns remain usable. The single-receipt screen uses neutral amounts and explicitly describes item-price coverage.

## Validation

Initial integration validation covered append/focus/retry/conflicting overlap, unavailable spending, saved-review content/revisions, duplicate candidates, currency safeguards and the HTTP Excel-download contract. The teammate's selected schema, parser, local OCR and photo suites passed (37 tests). Browser verification passed actual photo extraction, saved edits, mobile width, focus, append and return to collection without browser script errors. Existing outlook/chart/shopper navigation checks also passed. Mobile table overflow and a duplicate initial page render were found and corrected during verification.

After performance changes, the focused analytics/import/OCR-fallback suite passed 26 tests, parser checks passed 18 tests, and all 12 workspace tests passed, including the full-workbook HTTP import within its two-minute limit. Full workbook reports and both OCR fixture outputs compare exactly equal with the pre-optimisation snapshots. See the performance review for measured timings and their limits.
