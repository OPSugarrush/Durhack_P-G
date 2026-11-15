# OCR reintegration review

The original teammate folder was fetched again from `feature/my-name` at `f1fe8d5b3201d807d4e2b367f8509dcae11da079` and fully extracted to `reference/teammate_ocr/receipt_ingestion/`. That copy is unchanged. The active extraction modules matched it before this review, so the initial integration had not replaced the original image/layout algorithm.

The original uses geometric text grouping, a dark-ink pass for faint reverse print, guarded separate-column alignment, quantity-glyph rereading, explicit quantity/unit-price rows, weighted items and wrapped descriptions. Its Tesco fixture checks seven products, a panini discount and a net total of 16.72.

Running the actual supplied images through the original code found three priced products and a 14.60 total in the first image, and seven products and a 16.72 total in the second. The second image correctly linked the -0.73 discount to the panini. Some product spellings remained imperfect. The first image's joined date/time text was not parsed, so the active parser now inserts parsing-only separators and supports explicit AM/PM, including midnight/noon. It still leaves genuinely ambiguous dates unresolved and does not invent quantities where only item totals are printed.

Customer and receipt IDs now use the original exporter `new_id` function (C-/R- followed by a UUID). The main photo flow requires only a generated or reused customer ID and a file. Extracted metadata and product rows are displayed read-only by default; correction fields and OCR evidence are collapsed. Add/focus actions confirm the displayed extraction. Optional edits are saved and validated before use.

No receipt is loaded on startup, and the user-facing example entry points have been removed. Test fixtures and the original standalone example remain as source/testing assets, not default application data. Testing is done in a separate server instance; the handoff instance starts empty.

Receipt reading remains local. Recognition scores are not business-confidence scores. Item rows, printed quantities and pack sizes are distinct: seven product rows with quantity one do not mean that '2 Pack', 'X36' or '52 Pack' are purchase quantities.

Validation: all 29 original tracked files exist in the reference copy. The selected parser, actual OCR, Tesco-layout and application import tests passed (26 tests). Both supplied images passed the browser workflow: 3 and 7 product rows respectively, dates extracted automatically, generated UUID reused for the same customer, correction forms collapsed, focus navigation and no mobile page overflow. Preview URLs now include the batch ID so a previous receipt image cannot be reused for a different extraction. No supplied receipt image was copied into tracked source files.

A further large-preview regression passed, bringing the focused checks to 27. Binary responses now use HTTP/1.1 and explicitly flushed chunks; the browser decoded and displayed the larger Tesco image correctly after this adjustment. The final screenshot was visually checked against the uploaded photo. The handoff server starts empty on port 8772; the populated test servers are separate.
