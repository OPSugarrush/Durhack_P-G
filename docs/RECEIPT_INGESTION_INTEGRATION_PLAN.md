# Receipt ingestion: investigation and proposed integration

## Review refinement: proposed build contract

Status: planning only. The current browser application remains the UI technology: HTML/CSS/JavaScript served by the existing Python server. No Streamlit page, iframe, second server or Streamlit dependency is required by the integrated OCR feature. Existing unrelated dependencies need not be removed as part of this work.

### Repository logic is the foundation

The actual implementation baseline is the copied teammate commit named below. Reuse its `images.py`, `ocr.py`, `receipt_parser.py`, `models.py`, `parsing.py`, `validation.py` and `export.py`. The browser review replaces only the responsibilities of its `app.py`: displaying images, collecting edits, acknowledging review and requesting exports. Do not substitute an LLM extractor, rewrite the parser, or build a second conversion algorithm.

During integration, package the existing `receipt_ingestion/ingestion` directory under an explicit package mapping, with a namespaced import such as `needstate_receipt_ingestion`. Its internal relative imports already support this. This keeps one maintained implementation in the teammate folder rather than copying core files into a second location. Verify installation and teammate tests with that mapping; their standalone launch can continue to use its existing local imports. Keep OCR imports lazy and the new dependency group independent of Streamlit.

Changes to the teammate core should be narrow and evidenced: surface ambiguous leading-quantity interpretation for review, and reconcile promotion semantics through the adapter. Preserve their regression fixtures and compare behavior before and after any parser change. Pin the source revision in documentation so future updates can be reviewed as differences, rather than overwriting local integration changes blindly.

### Audit of the first plan

| Initial idea | Decision after checking current code |
|---|---|
| Reuse workbook format | Keep. Use `export.dataframe` and the existing mapping internally; Excel generation is a download option. |
| Separate collection and focus | Keep. Focus must not overwrite `Store.lines` or discard the collection's cached report. |
| Call the full analytics pipeline for every upload | Refine. One receipt should use `process_lines` for existing product/category resolution and a descriptive summary, without running population trend analysis. |
| Reuse `combine` for append | Keep, with additional source/retry checks. Its receipt-ID conflict behavior is valuable; it cannot recognize a rephotographed receipt with a new ID. |
| Require all fields to be complete | Reject. Missing address or unit price should not block an otherwise useful receipt. Gate the affected analysis instead. |
| Treat missing spend as reduced coverage | Strengthen. `spending_profiles` sums all-null amounts to zero. Views must distinguish unavailable spend from an actual zero and avoid a misleading budget/scenario output. |
| Append only the new results | Reject. New dates change the midpoint comparison, and product resolution is dataset-dependent. Re-run the existing engine on combined canonical rows; do not concatenate reports or compare changed rankings as if the period stayed fixed. |
| Automatically deduplicate similar receipts | Reject. Similar baskets can be legitimate repeat purchases. Exact identities can be skipped; uncertain matches require a simple user decision. |
| Add broad dataset management | Defer. One collection and one temporary upload cover the requested flow. Avoid projects, many saved workspaces and a database in this iteration. |

### User-facing layout and behavior

Use the existing Import navigation item. The page begins with the collection summary, if present: receipt count and recorded date range. Below it are two source tabs, Spreadsheet and Receipt photo. The selected tab contains one upload area. After parsing, keep the user on the same page and show a review section below it.

For a photo, place the image beside an editable product table on wide screens; stack them on narrow screens. The primary columns are Product, Quantity, Unit price and Line total. Receipt date, store, total and shopper sit above the table. Show item discounts when present, with other row types and original OCR under “Other receipt lines” and “Extraction details”. Unknown fields are visibly blank, never prefilled with zero or one. Unclassified priced rows need an explicit classify/exclude decision so hiding them cannot silently omit a purchase.

Place a short issue summary above the actions: for example, “Confirm the date and review 2 items.” Link each issue to its field or row. A generic confirmation checkbox cannot override errors that make the chosen action invalid. After any edit, revalidate the entire receipt and invalidate previous review acceptance. Keep the original extraction available for comparison.

For a spreadsheet, use a compact summary rather than rendering thousands of rows: receipt count, shopper count, date range, price coverage, and duplicate/conflict counts. Show a small preview and offer targeted problematic-row details. Spreadsheet cell editing is outside the first build; give actionable errors for correction and re-upload.

After review, place **Add to my data** and **Focus on this upload** together, each with one line explaining the effect. Adding switches to the updated collection. Focusing switches to the upload's summary or insights, with a scope banner such as “Viewing this upload · 1 receipt” and a **Back to all data** link when a collection exists. A focused upload may later be added through a secondary action; once added, show “Added to your data” and disable duplicate submission.

One receipt opens a compact receipt overview, not Business outlook. It shows recorded purchases, known category totals, merchant/date and review status. Suggested shopping purpose, if shown later, must use existing inference and be clearly labelled an interpretation; defer it from the first receipt view. Multiple receipts from one shopper may support an individual history, but not population-level investment conclusions. A larger upload uses existing insight thresholds and provides useful descriptive coverage even when no trend qualifies.

Opening a new upload should prompt only if it would discard unsaved review edits. Switching away and returning during the session should retain the current draft. Resetting/restarting the local server clears this session data; label it “Data in this session” rather than promising permanent storage.

### Minimal internal state and API responsibilities

Keep these responsibilities separate, without introducing a new framework:

- `Collection`: canonical rows, source provenance, revision, completed report.
- `UploadBatch`: stable ID, source hash/type, original extraction or parsed rows, current edits, review revision, issues and intended shopper association. Limit the first build to one active staged upload.
- `ActiveView`: collection or upload ID and the completed report revision for that scope.
- `Job`: extraction/analysis status and stage. Browsing the last complete report remains possible during work.

Proposed API responsibilities (names may be adjusted to existing conventions): create spreadsheet/photo batch; fetch review; submit receipt edits; commit batch with `append` or `focus`; select collection view; retrieve scope-specific report/evidence. Preserve the current workspace-token and loopback checks. An explicit `batch_id` and review revision bind confirmation to exactly the content reviewed. Do not accept an arbitrary client-side dataframe as already validated.

Serialize mutation/analysis jobs for the initial build. A commit includes the expected collection revision. Repeated requests for the same batch/action return the completed result instead of appending again. Build a candidate dataset and report off to the side, then publish them together on success. Extraction errors, analysis errors and browser retries must not alter accepted collection data.

Report/evidence requests should include their expected scope and report version. Evidence currently uses finding indexes, which can refer to different findings after a report change. On mismatch, refresh the page context instead of returning another scope's customers. The frontend's route epoch guard helps with late responses but does not replace this server-side check.

Keep raw image bytes and OCR evidence only for the active session and serve previews through a bounded local endpoint using opaque IDs. Release replaced/discarded drafts. Do not put raw OCR or file bytes into normal findings responses. Escape edited product names exactly as existing UI text. Preserve image/PDF bounds and set the upload size consistently in the frontend and server.

### Data acceptance rules

| Condition | Planned handling |
|---|---|
| No accepted product descriptions | Stay in review; cannot append or analyse. |
| Date absent or ambiguous | Permit draft/export; require correction for entry into the current canonical analytics dataset. Do not invent a date. |
| Time absent | Accept a known date; retain date-only precision in provenance and suppress time-of-day claims. |
| Quantity or unit price absent | Accept usable product/amount data; do not derive unprinted values automatically. |
| All line prices missing | Category/item summary remains useful; show spend unavailable and suppress spending scenarios. |
| Some prices missing | Show known-item spend and price coverage; do not call it complete basket spend. |
| Printed total differs from item sum | Show both and the discrepancy; retain basket adjustments separately. Do not silently distribute discounts. |
| Unknown shopper | Allow an explicitly new pseudonymous shopper or an unlinked receipt. Never group all unlinked receipts into one household. Unlinked receipts contribute only to analyses that do not require customer identity. |
| Same receipt ID, identical content | Skip and report it. |
| Same receipt ID, different content | Block that append with a conflict explanation; no implicit overwrite. Receipt correction/replacement is a later separate action. |
| Same photo bytes already accepted | Show the existing receipt and prevent automatic re-addition. |
| Similar content with different IDs/photos | Show possible duplicate and require Keep separate / Skip. Record the decision. |
| Synthetic demo versus real photo | Maintain explicit source labels; demo mode is separate from the user's collection. Do not silently mix example data with uploaded data. |

Unknown currency is not permission to assume GBP. If the spreadsheet's currency is not declared, capture a dataset-level currency choice or show neutral amounts. Do not offer combined monetary insights across incompatible/unknown currencies; category counts can remain available. Real-photo support also requires replacing the current synthetic-only declaration with an accurate local-data workflow. This is part of the planned import change, not a reason to mark real photos as synthetic.

### Delivery boundary and acceptance checks

Build in three reviewable increments: (1) spreadsheet staging, append/focus and scope consistency; (2) teammate OCR packaging and browser receipt review; (3) descriptive receipt view, provenance, duplicate handling and end-to-end checks. No new investment model or replacement frontend framework is needed.

Meaningful tests should exercise outcomes: focus then return preserves collection counts; append unions receipt rows and recomputes the date range; retry counts a batch once; conflicting overlap keeps all prior data; stale evidence cannot display a different scope; missing prices are not shown as zero spend; invalid dates cannot enter time analysis; one receipt cannot generate trend claims; photo edits survive conversion; item and basket discounts are not double counted. Run the teammate parser/export tests and actual local OCR fixtures after installing the optional dependencies, then manually exercise photo and workbook journeys in the existing browser UI.

Current verification remains source inspection only: the prior attempted teammate tests could not collect because `pydantic` is missing. The full-workbook analysis timeout identified in the earlier app audit also remains an existing performance concern; stage feedback helps explain progress, but it does not fix runtime. Measure append and focus latency with the real workbook during implementation before claiming the workflow is ready.

## Scope and source

Copied the complete `receipt_ingestion/` directory from `origin/feature/my-name`, fetched commit `f1fe8d5b3201d807d4e2b367f8509dcae11da079`. No existing application files were changed. The folder is a standalone teammate application, including its examples, tests, dependency files and Streamlit interface. Instructions in its README describe that standalone application; they are not instructions to replace our interface.

This document proposes integration only. No photo endpoint, data-selection feature, dependency installation, or application integration has been implemented.

## What the code does

1. `ingestion/images.py` decodes JPG/PNG or up to five PDF pages of one receipt. It applies EXIF orientation, limits image dimensions and upload size, and prepares in-memory images.
2. `ingestion/ocr.py` runs package-bundled RapidOCR/ONNX models on the CPU. It groups positioned text boxes into rows and retains recognition scores. A second dark-ink pass and guarded column alignment support a particular receipt layout. There is no remote inference or API key.
3. `ingestion/receipt_parser.py` classifies products, discounts, totals, taxes, payments and unclassified text. It parses dates, prices, explicit quantities and adjacent detail lines. Ambiguous fields usually remain blank for review.
4. `ingestion/models.py` and `parsing.py` validate extracted records and human edits with Pydantic. `validation.py` checks missing fields, item counts, contribution to totals and arithmetic using Decimal.
5. `ingestion/export.py` exports only product rows in the existing 14-column workbook format. JSON additionally retains the original extraction, edited receipt, source hash, uncertainty, adjustments and OCR evidence.
6. `app.py` supplies the standalone review interface. Its extraction, edit and export functions can be reused without embedding Streamlit in our browser application.

The module is an input converter. Product families, categories, brands, customer histories and business conclusions should continue to come from the existing analysis engine.

## Proposed user journey

Keep one Import page with two choices: **Spreadsheet** and **Receipt photo**. Show supported file types beneath the relevant choice. PDF can be an additional supported receipt format because the code already handles it.

Photo journey: upload → extract → review image beside editable products → confirm → choose how to use the data. Ask which shopper the receipt belongs to, with an existing pseudonymous ID or a new shopper. Never automatically assign it to an existing shopper. Show a simple extraction status, not an OCR score as a business confidence rating.

Spreadsheet journey: upload → validate → show receipt/shopper counts, date range and duplicates → choose how to use the data. A spreadsheet containing one receipt should receive the same receipt-level experience as a photo.

Use the same two actions after either review:

- **Add to my data**: append accepted receipts to the collection; skip verified duplicates; recalculate the collection's insights. Show what will be added before confirmation.
- **Focus on this upload**: analyse the uploaded batch separately and leave the collection intact. Display a persistent scope label and **Back to all data**. Merely focusing should not make the upload part of the collection.

For the first upload, these actions still have different meanings: creating the collection versus viewing a temporary upload. Explain this with one short line. Do not introduce a separate replacement action unless users need it later.

## Separate collection from active view

The server currently holds one `Store.lines` and one report. Each import replaces them. Introduce two small concepts rather than rebuilding the analytics architecture:

- Collection: accepted canonical rows and their source records.
- Active scope: the collection or a temporary upload, with its own report and version.

An upload first becomes a staged batch. Extraction and edits do not mutate the collection. Appending validates and combines the candidate rows, completes analysis, then atomically publishes the new collection/report. Errors retain the previous collection. Focusing publishes only a temporary view; returning restores the collection report. Keep the current import lock and background processing pattern. A small in-memory batch/source registry is sufficient for the current local app; persistence across restarts is a separate feature, not implied by “saved collection”.

Both photo and spreadsheet routes should converge before this staging/commit boundary. Their parsing differs; their append, duplicate, focus and analysis behaviour should not.

## Connect to the existing code

- Reuse `prepare_images`, `extract_receipt`, `edited_receipt`, `check_receipt` and `export.dataframe` through a thin adapter. Do not import or run the teammate's `app.py` inside our server.
- Convert the reviewed photo's dataframe with the existing mapping and `to_canonical`. Keep Excel download as an option, rather than creating and re-reading Excel internally. Factor out shared row validation so this route receives the same ID/line checks as `workspace.workbook`.
- Keep `workspace.workbook` for spreadsheet parsing. Both routes then produce canonical rows plus provenance and validation results.
- Reuse `workspace.combine` for receipt-ID overlap checks. It already skips identical receipts and rejects conflicting overlaps, but `webapp.Store.run` does not currently call it. Add separate source-level duplicate detection around it.
- Continue calling `analyse_lines` for eligible scopes. Make scope/version information available in state so navigation cannot mix collection and focused-upload results.
- Keep original OCR, adjustments, review status and source hashes in a sidecar keyed by receipt ID. The canonical line table and Excel format cannot retain all of this evidence.
- Package the ingestion core explicitly when integrating: the root project currently discovers packages only under `src`. The standalone imports named `ingestion` assume its folder is on the Python path. Use a deliberate namespaced package/adapter rather than global path manipulation. Preserve the copied folder as the reference until integration is reviewed.

## Match insights to the available evidence

One receipt supports a basket summary: purchased products, categories, identified brands, spend where known, and observed promotions. It does not establish change, repeat behaviour, switching or investment opportunities. Explain briefly: “Add more receipts to see how purchases change.” Do not fill the business-outlook page with empty trend charts or extrapolate a single basket into a company recommendation.

A focused spreadsheet may contain enough history for normal insights. Use its own coverage and evidence gates; never borrow history from the collection while claiming to describe only the upload. Appending a receipt can contribute to existing history only when its shopper ID is deliberately matched. Existing evidence thresholds remain responsible for whether a trend is supported.

OCR confidence concerns transcription. Review status concerns acceptance of extracted data. Business confidence concerns patterns across purchases. Keep these separate in both data and UI.

## Issues to address during integration

1. **Duplicate photos:** every extraction generates a fresh UUID, so `combine` alone cannot prevent double counting. Retain the file SHA-256 and reuse a staged receipt ID on retries. Block repeated accepted source hashes by default. Resized or rephotographed receipts need a potential-duplicate check using shopper, date, store, totals and items; ask for confirmation rather than silently deleting a legitimate repeat trip. Cross-source overlap with workbook receipts also needs this check.
2. **Missing date:** OCR permits a null date; canonical ingestion rejects invalid/missing timestamps. Allow draft review/export, but require a corrected date for timeline analysis. Do not substitute today's date. Time can remain unknown; the existing adapter falls back to the date, which must not become a claimed midnight shopping time.
3. **Unknown amounts:** do not invent quantity 1, unit prices or missing totals. Permit supported descriptive insights when spend fields are missing and explain reduced spend coverage. Verify downstream handling before enabling this path.
4. **Leading quantities:** the parser treats `2 PRODUCT 1.50` as two units at 1.50 and sets the line total to 3.00. Other retailers may print a line total there. This assumption needs explicit review or stronger layout evidence; it is not universally safe.
5. **Promotions:** the photo dataframe exports a negative numeric adjustment. Existing `to_canonical` treats any non-null promotion field, including zero, as promoted; the JSON route uses a different truthiness rule. Define a shared explicit rule before integration. Keep basket coupons separate from item adjustments, and do not infer an absent promotion from missing evidence.
6. **Totals and currency:** receipt totals repeat on every product row and must never be summed as line spend. Excel omits standalone basket adjustments and currency. Retain those in provenance; do not force reconciliation or aggregate incompatible currencies without an explicit rule.
7. **Review gates:** the standalone UI permits export after acknowledging unresolved warnings. Analysis needs a distinction between blocking errors (no products, invalid date/IDs, invalid required data) and warnings that limit which insights are usable. Missing postal address should not block category analysis. Arithmetic passing does not prove OCR correctness.
8. **Privacy declaration:** the current app explicitly accepts synthetic spreadsheets only. Actual photos would change that product boundary. Decide the intended data policy and update the declaration, evidence handling and retention honestly before enabling real-photo import; do not label real receipts synthetic to bypass the gate. Avoid exposing OCR text or shopper IDs unnecessarily.
9. **Runtime:** OCR dependencies are not installed by the root project's declared requirements. Add an explicit optional dependency group and a helpful unavailable-state message. Lazy-load OCR so spreadsheets remain usable without it. Bound extraction concurrency, because the cached engine is shared and concurrent use is not established by the current tests. Reconcile the app's 16 MB upload limit with the module's 20 MB limit.
10. **Validation evidence:** `TEST_RESULTS.md` reports 34 passing tests from the teammate's environment. It also says no real photographs were supplied, while the later README and tests include `examples/test1.jpg`; treat those claims as historical, not a current accuracy benchmark. Inspect example privacy before wider distribution. Fixture success does not establish performance across retailers.

## Suggested implementation order after review

1. Introduce staged uploads and collection/focus actions for spreadsheets first. Prove append, duplicate/conflict handling, return-to-collection behaviour and report-version consistency.
2. Add a small receipt-level view so one-receipt uploads are useful without claiming trends.
3. Package the OCR core and add photo extraction/review, feeding accepted rows into the same staged-upload flow.
4. Preserve provenance and cross-source duplicate checks; verify missing-field and promotion handling.
5. Test end to end: focused uploads never alter the collection; failed appends preserve it; repeated photos are not double counted; human corrections survive; one receipt produces no trend claims; sufficiently rich uploaded histories use the existing insight engine.

No additional forecasting, brand inference or investment scoring belongs in this ingestion work.

## Local verification of this investigation

The folder was extracted from the fetched Git commit, without merging the teammate's branch. Source inspection covered the image loader, OCR, parser, models, review flow, validation, exports and the current app's import/state/canonical conversion. A local attempt to run `test_schema.py` and `test_pipeline.py` stopped during collection because this app's environment lacks `pydantic`. No dependency installation was performed, and no fresh OCR execution or accuracy result is claimed. Existing application files remain unchanged; the only additions are the copied folder and this plan.
