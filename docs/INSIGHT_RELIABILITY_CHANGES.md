# Insight reliability changes

Local follow-up to audit commit 39cf301. No new navigation sections or statistical models.

- Shared backend evidence gate: both Findings and Business outlook require sufficient comparable buyers/category buyers, corrected evidence, a nonzero interval and directional agreement. A large mean driven by a minority cannot by itself pass the combined direction check.
- Category monthly histories now include zero purchases when other receipts exist, and explicitly distinguish periods with no observed trips.
- Category details show the three most frequently observed recent product descriptions and offer a downloadable investigation brief containing the cohort, comparison dates, evidence, next action, alternative explanations and suggested evaluation. Product counts are descriptive, not proof those products caused the category change.
- Reports have dataset version identifiers; navigation refreshes a stale cached report, and import completion refreshes outlook even when already on that route.
- Imports expose their current analysis stage.

Validation: 19 focused non-HTTP tests passed; the full-workbook HTTP check still exceeded its two-minute deadline. Browser checks passed for the sample journey, new brief download, brand/profile navigation and mobile overflow. JavaScript syntax checks passed.

Performance profiling found time in receipt grouping/string operations and graph decomposition. A trial string-representation change did not meet the import deadline and was removed. No performance speedup is claimed. Further profiling/optimisation is still required before relying on the full workbook for a timed demo. Import limits and test deadlines were not relaxed to hide the failure.

Dataset version checks improve navigation freshness but do not implement transactional cross-tab evidence requests. Brand uncertainty, financial completeness and persisted experiments remain future work.
