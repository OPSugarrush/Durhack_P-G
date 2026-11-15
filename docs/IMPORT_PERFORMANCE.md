# Import performance review

The analysis rules, thresholds, confidence calculations and OCR parser are unchanged.

## Changes

- Build shopper brand histories from grouped receipt sets rather than repeatedly filtering and copying small pandas frames. Precompute monthly category denominators and reuse category eligibility across brand and owner calculations.
- Use connected components directly when a basket graph is a disconnected union of constant-weight cliques. These have the same greedy-modularity partition. All other graphs retain the original algorithm.
- Run the dark-ink OCR pass first. When geometric alignment succeeds, omit the normal-image scan whose output was previously discarded. Otherwise run the original fallback with its original thresholds, restoring RapidOCR's persistent settings afterwards.
- Reuse the current batch's completed analysis for repeated focus and adding it to an empty collection. Reuse collection analysis for identical appended receipts, after overlap validation. Config changes or saved receipt edits invalidate reuse.
- Cache the last two photo extractions within the session. Each review receives an independent copy and a fresh receipt identifier. Accepted duplicate photos remain rejected.
- Keep source evidence without deep-copying full reports and canonical frames into each source record.

## Measurements and checks

The local workbook contains 32,776 item rows and 3,005 receipts. Profiled cold runs took 501.96 seconds before and 151.60 seconds after. The final category/brand/spending stage fell from 421.13 to 25.73 seconds. A normal run without profiling completed in 57.98 seconds, including imports and workbook parsing. These are local observations, not guaranteed timings: system load, first-time imports and profiling overhead affect them.

Complete serialized workbook reports compare equal before/after, including the final normal run. Complete extracted receipt objects also compare equal for the simple example and photographed Tesco receipt. The Tesco path now uses one full OCR pass instead of two; receipts that need fallback still use two. OCR timings were collected under different competing loads, so no fixed OCR speed multiplier is claimed.

`scripts/profile_performance.py --mode workbook --label NAME` records profiles, timings and full report snapshots in ignored `artifacts/performance/`. Use `--mode ocr` for both receipt fixtures, or `--no-profile` for normal wall time. Regression tests cover graph equivalence, brand histories, OCR fallback settings, upload reuse and edit invalidation.

The unchanged teammate source remains under `reference/teammate_ocr/receipt_ingestion`. Optimisations apply only to the active implementation. Data and caches remain session-local and are cleared when that server stops.
