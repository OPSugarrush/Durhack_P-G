# Hackathon brief audit and additive delivery plan

Audited base: `a288724` (teammate branch `feature/customer-intelligence-workspace`). Review branch: `audit/hackathon-brief-gap-review`.

This is a source-code audit, not a claim of fresh runtime validation. No application code was changed. Both supplied texts were read; both end section 7 with the incomplete word/sentence “Enable”. Any missing continuation remains unaudited.

## Assessment

The submission has a substantial descriptive foundation: product resolution, basket interpretation, customer routines, uncertainty checks and traceable evidence. Its custom web interface is usable for investigating findings. It does not yet demonstrate validated future prediction or goal-based prescription. Calling the mission inference function `predict_basket` does not make it predictive in the brief’s sense: it interprets purchases already observed.

The largest gap is consumer value. Receipt-level prices are visible, but there is no spending overview, savings calculation, budget, goal or feedback loop. Business evidence is stronger, but it mostly stops before a decision, alternative action and measurable outcome.

Status key: **Covered** = an implemented capability addresses the item; **Partial** = meaningful implementation exists but scope, exposure or outcome is incomplete; **Missing** = no implementation located. Coverage does not certify real-world efficacy. Backend/legacy features are distinguished from the current web journey.

## Evidence register

References below use repository paths and exact symbols so reviewers can locate the implementation without relying on changing line numbers.

- **E1 — Import and history:** `src/needstate/workspace.py`: `workbook`, `combine`, `behaviour`, `analyse_lines`. Validates XLSX, preserves IDs, rejects conflicting numbered lines, connects dated trips to buyers. `combine` exists but is not called by current web imports.
- **E2 — Current product:** `src/needstate/webapp.py`: `Store.run`, `Handler`; `src/needstate/web/app.js`: `importPage`, `findings`, `mainFinding`, `evidence`, `buyerReason`, `cohort`. Each upload replaces the in-memory analysis. Buyer views show receipts supporting a selected finding, not an exhaustive financial account. Main findings and exploratory observations have separate tabs.
- **E3 — Resolution:** `src/needstate/product_intel/entity_resolution.py`: `fold`, `expand`, `resolve_products`; `product_intel/hierarchy.py`: `build_hierarchy`, `attach_hierarchy`; `configs/hierarchy.yaml`. Families, nullable brand/owner, function and category metadata. Tests in `tests/test_product_intel.py` cover abbreviations, truncations and pack-size non-merges.
- **E4 — Basket evidence:** `need_state/decomposition.py`: `decompose_basket`; `need_state/inference.py`: `predict_basket`; `need_state/observations.py`: `period_pairs`, `replicated_pairs`, `group_status`. Current web pair corroboration conditions on buyer and basket size and requires replication across periods. It uses a normal approximation to conditional pair moments; it is not the legacy permutation engine.
- **E5 — Analytical engine:** `patterns/cooccurrence.py`: `null_model_pairs`, `bootstrap_pair_ci`; `patterns/trends.py`: `trend_scan`, `hierarchical_scan`, `brand_share_decomposition`; `service.py`: `analyse`. Consumer-adjusted co-purchase and historical trends exist in CLI/legacy analytics. Brand prevalence decomposition is not a same-person switching detector.
- **E6 — Routines:** `patterns/routines.py`: `concentration`, `repeat_rates`; `patterns/transitions.py`: `entry_exit`; `app/pages/4_Consumer_Routines.py`. Entry/exit is presence between adjacent observed receipts, not demonstrated brand substitution.
- **E7 — Quality:** `validation/checks.py`: `reconcile`, `receipt_quality`; `missing_data/simulation.py`: `corrupt_lines`; `missing_data/evaluation.py`: `evaluate_corruption`; `validation_harness/injection.py`: trend/bundle injection, recovery and false-alarm routines. Tests exist in `tests/test_foundation.py`, `test_patterns.py`, `test_misc.py`. Clean-baseline agreement measures stability, not truth about motivations.
- **E8 — Discovery/review:** `discovery/candidates.py`: `discover_candidates`; `ai/llm.py`: `describe_candidate`; `reliability/review_queue.py`; `mission_review.py`: `compare`. Candidate communities, template narration and review support exist. Candidate records explicitly start with held-out replication and human review false. The web Exploratory tab currently groups weaker/category observations; it does not expose the full discovery review workflow.
- **E9 — Portfolio:** `product_intel/portfolio.py`: `PortfolioLens`; `app/_common.py`: `lens_sidebar`; `app/pages/2_Pattern_Engine.py`. Configurable portfolio exposure/adjacency exists in legacy analysis, not a portfolio decision workflow in the current web UI.
- **E10 — Provenance:** `config.py` synthetic setting, legacy `synthetic_banner`, and web `Store.sample`. The web sample flag identifies the built-in demo only; uploaded synthetic workbooks are not separately identified in that flag. Import has no explicit permitted-data declaration.

## A. Requirement checklist

### Sections 1–2: objective and problem

| Requirement | Status | Evidence and remaining gap |
|---|---|---|
| P&G/DurHack, 24-hour behavioural analytics challenge | Covered as project context | Existing receipt-focused implementation and configuration; duration is a delivery constraint, not a feature. Prioritise the plan below accordingly. |
| Transform messy receipts into reliable continuous insights | Partial | E1/E3/E7 handle messy inputs; E2 replaces each dataset and loses history on restart. Continuous observation requires cumulative input or managed history. |
| Value for both consumers and P&G | Partial | E4–E9 support business investigation; consumer tools are missing (section 6). |
| Interpretation rather than an OCR challenge | Covered | E1 consumes extracted rows; E3 normalises text; E4 interprets baskets. No new OCR engine needed. |
| Receipts are partial snapshots of household purchasing | Partial | E1 joins observed buyer IDs; E7 models degradation. Neither establishes household identity nor purchases outside the records. |
| Reconstruct weeks/months despite inconsistent descriptions | Partial | E1 dated buyer histories and E3 family matching help; no inferred missing-trip reconstruction or persistence. |
| Acknowledge missing-data uncertainty | Covered with UI gap | E7 quality/abstention and corruption analysis; E2 exposes receipt scores but not the full reliability experiment results. |
| Understand actual shopping beyond surveys/isolated purchases | Partial | E1/E6 repeated observed purchases; synthetic data cannot establish real household behaviour. |

### Section 3: every key question

| Question | Status | Checked evidence / boundary |
|---|---|---|
| What products are consumers buying? | Covered | E1/E3 resolve products; E2 shows supporting products and purchase counts. |
| Which products appear together in one basket? | Covered | E4 partitions baskets; E2 displays products and mixed missions. |
| Which products are frequently bought alongside one another? | Covered, exposure partial | E4 replicated pairs and E5 adjusted pair analysis. Dedicated ranked pair evidence is mainly legacy. |
| How do patterns repeat over time? | Covered | E1 established routines; E6 repeat rates; E4 two-period corroboration. |
| How do habits change across weeks/months? | Partial | E1/E2 dated midpoint comparisons and E5 historical monthly trends; no flexible rolling monitoring in current web. |
| When do consumers switch between brands? | Partial | E3 brand metadata, E6 entry/exit and E5 brand/category decomposition are ingredients; no paired brand-to-brand timeline or sustained-switch criterion. |
| What motivates trying new products? | Missing | Mission hypotheses describe product uses, not reasons for trial. E8 narrator explicitly disclaims motivation; optional feedback text is displayed by E2 but not analysed as evidence of trial motives. |
| How do consumers respond to promotions? | Partial | Promotion labels retained by ingestion; legacy audit states retailer confounding. No response comparison/estimate. Missing labels mean unknown, not non-promoted. |
| Reconstruct months from partial records? | Partial | E1 reconstructs observed chronology; E7 evaluates missingness. Unseen purchases are not recovered and should not be presented as facts. |
| Reliable insights despite missing/inconsistent information? | Covered, validation limited | E3/E4/E7 resolution, abstention, conditional evidence and degradation experiments. Real intent accuracy remains unvalidated. |

### Section 4: data and restrictions

| Brief item | Status | Evidence / interpretation |
|---|---|---|
| Supplied synthetic Excel database | Covered | E1 mapping/XLSX import; supplied-format tests in `tests/test_real_file.py`. |
| OCR already extracted; post-OCR rows rather than image processing | Covered | E1/E3 directly consume and clean product text. |
| Different shops | Covered at ingestion | Retailer/store fields retained; retailer effects not causal conclusions. |
| Different basket sizes | Covered | E4 conditions pair evidence on size; decomposition supports mixed baskets. |
| Different purchase types | Covered | Configured function/category hierarchy and multi-need baskets. |
| Inconsistent product names | Covered | E3 normalisation and review candidates. |
| Abbreviated/truncated descriptions | Covered | E3 expansion and family resolution; ambiguous matches retain review needs. |
| Messy/incomplete records | Covered | E1 validation, E7 quality and missingness handling. |
| Synthetic data imitates real information problems | Partial | E7 stress tests workflow robustness; no external validity claim justified. |
| Open-source data may supplement provided data | Partial, optional | Mapping/canonical layer supports reuse; current web uses one configured schema/file. No curated external source included. |
| Open-source data may replace provided data | Partial, optional | CLI/config adapters permit alternate sources; no dedicated source provenance/licence flow. |
| Open image datasets may create a dataset | Missing, optional | No image pipeline; permission in the brief is not a requirement to add one. |
| Do not use or collect real personal data/real shopper receipts | Partial | Built-in demo is synthetic and app is local, but E2 accepts arbitrary files without a declaration. Local storage does not satisfy this restriction by itself. Add a scope guard, not a claim of automatic personal-data detection. |

### Section 5: every P&G value point

| Value point | Status | Evidence / remaining need |
|---|---|---|
| Observe continuously rather than occasional surveys | Partial | E1 dated histories, but E2 replacement-only imports and in-memory lifecycle. |
| Analyse complete shopping baskets | Covered for supplied records | E4 includes whole recorded baskets; completeness checks do not prove every real purchase was supplied. |
| Identify frequently co-purchased products | Covered | E4/E5 adjusted associations. |
| Discover different consumer groups | Partial | E1 behaviour-specific cohorts; no stable cross-category segmentation or segment profiles. |
| Identify recurring routines | Covered | E1/E6. |
| Understand switching among competing brands | Partial | E3/E5/E6 ingredients; no explicit switch analysis. |
| Examine changes over time | Covered descriptively | E1/E5; no validated forecasts. |
| Improve product/category understanding | Covered descriptively | E3/E4/E5 with receipt traceability. |
| Faster, better-informed product decisions | Partial | Findings are accessible (E2), but decision options and outcomes are absent. |
| Evidence-supported innovation decisions | Partial | E8 discovery hypotheses/review; no opportunity validation brief. |
| Consumer segmentation | Partial | Behaviour cohorts exist; not sustained segments or intervention-specific audiences. |
| Product portfolio strategy | Partial | E9 lens and E5 decomposition, no tradeoff comparison. |
| SKU rationalisation | Missing | Product families exist, but no reliable SKU-level contribution, margin, substitution or removal-impact model. |
| Product innovation | Partial | E8 hypotheses; no evidence-to-experiment plan. |
| Category strategy | Partial | E5 changes and E9 exposure; no measurable strategy recommendation. |
| Shopper strategy | Partial | Missions and cohorts E1/E4 support targeting hypotheses; no tested intervention. |

### Section 6: every consumer value point

| Value point | Status | Evidence / missing capability |
|---|---|---|
| Understand spending patterns | Partial | E2 shows unit prices on supporting receipts. No category/monthly totals, quantity-aware spend summary or reconciliation display. |
| Find savings opportunities | Missing | No comparable-price/unit-price savings engine; raw unit price alone cannot compare different pack sizes. |
| Personal budgeting | Missing | No budget entry, spending forecast or budget gap. |
| Helpful recommendations/nudges | Missing | E8 research narration is not a consumer nudge. |
| Influence future spending | Missing | No action/what-if comparison or follow-up. |
| Long-term behaviour change | Missing | No longitudinal intervention evaluation. |
| Achieve personal goals | Missing | No goal model, progress or user-selected constraints. |
| Reason to keep contributing data | Missing | No recurring consumer benefit/feedback loop; replacement imports alone do not provide one. |
| Consumer and business value encourages engagement/data sharing | Partial | Business research exists; consumer return is absent. For this hackathon, demonstrate engagement only with synthetic personas/permitted data. |

### Section 7: outcome levels, line by line

These levels describe outcomes, not a feature checklist in which “poor” limitations should be implemented. ROI ratios are illustrative brief claims, not measured targets or achieved returns.

| Level / statement | Status | Evidence and judgement |
|---|---|---|
| 1: What happened? | Covered | E1–E6 historical purchases and patterns. |
| Descriptive historical analysis | Covered | Current core capability. |
| Basic statistics/reporting | Covered | Counts, frequencies, changes, quality and uncertainty. |
| Limited motivation to keep contributing | Partial: limitation applies | No consumer goal/benefit loop. |
| Limited business value beyond observations | Partial: limitation applies | Corrected evidence improves trust, but actions/outcomes are absent. |
| Little evidence of influencing behaviour | Missing outcome evidence | No intervention trial. |
| Little evidence of enabling strategic decisions | Partial | Portfolio/discovery tools supply inputs, no decision evaluation. |
| Low return on investment | Missing measurement | No cost/benefit accounting; cannot classify actual ROI. |
| Illustrative 1:1 ROI | Missing measurement, not a requirement | Must not report as achieved. |
| 2: If this happens, what happens next? | Missing | No temporal forecast or scenario response model. |
| Predictive consumer analysis | Missing | Mission scoring interprets current baskets; trends describe history. |
| Understand/influence spending | Partial | Prices visible, forward spending support absent. |
| Budgeting/saving | Missing | No financial plan or savings action. |
| Useful nudges | Missing | No personalised action with expected benefit. |
| Incrementally inform product/category/shopper strategies | Partial | E5/E8/E9 evidence exists, no decision chain. |
| Continuous engagement reason | Missing | No consumer progress loop. |
| Value for consumers and P&G | Partial | Business-heavy current product. |
| Modest ROI | Missing measurement | Requires incremental benefit and cost evidence. |
| Illustrative 10:1 ROI | Missing measurement, not a requirement | Treat as illustration only. |
| 3: What should be done for a particular outcome? | Missing | No objective-driven action comparison. |
| Recommend actions producing desirable outcomes | Missing | No estimated intervention benefit or tested prescription. |
| Long-term behaviour change | Missing | No follow-up measurement. |
| Consumer goals | Missing | No goal-setting/progress. |
| Consultancy-grade business insights | Partial | Traceability and uncertainty are strong inputs; alternatives, assumptions, economics and validation plan missing. |
| Consumer segmentation | Partial | Observational cohorts, no durable segmentation. |
| Portfolio decisions | Partial | Lens exists; action comparison absent. |
| SKU rationalisation | Missing | No decision model or required commercial inputs. |
| Product innovation opportunities | Partial | E8 hypotheses/review, no opportunity-to-experiment workflow. |
| “Enable” | Not assessable | Both supplied briefs stop here. No requirement inferred. |

### Existing feature level and route toward excellent

| Existing feature | Present level | Additive path toward prescriptive value |
|---|---|---|
| Import/resolution/quality | Enabling foundation | Show coverage and provenance in action evidence; never substitute cleaning scores for outcome certainty. |
| Basket missions/mixed baskets | Descriptive | Use existing explanations as context for a proposed action and controlled experiment. |
| Routines/customer changes | Descriptive | Add temporal baselines, a user goal and constrained what-if choices. |
| Main findings/exploratory tabs | Descriptive | Attach next decision, expected benefit assumptions and success measure to existing findings. |
| Adjusted pairs/trends | Descriptive statistical evidence | Use as experiment inputs; co-purchase does not prove bundle intervention uplift. |
| Portfolio lens/brand decomposition | Descriptive | Compare portfolio options conditional on explicit margin and substitution assumptions. |
| Discovery/review/narration | Descriptive hypothesis generation | Convert approved evidence to an innovation experiment with a falsifiable outcome. |
| Missingness/injection validation | Reliability foundation | Extend to forecast calibration and prescription sensitivity without claiming real-world effectiveness. |

## B. Proposed additions (plan only)

No replacements or parallel dashboards are proposed. Implement in this order: data scope/coverage, consumer goals, supporting forecasts, then business action briefs. Switching/promotion context can follow as data permits.

### 1. Import provenance and history coverage — extension of Import and evidence

**Brief:** sections 1–2 continuous reliable insight; section 3 reconstruction/reliability; section 4 prohibition on real personal data.

**Location:** extend `webapp.py:Store.run`, `workspace.py:workbook/analyse_lines`, and `web/app.js:importPage/evidence`. Keep the teammate’s single-file import. Explain that a cumulative workbook is required for a longer history; do not silently restore multi-file append. Reuse `reconcile`/`receipt_quality` for a compact coverage report and preserve source provenance with the report.

**Experience:** choose permitted synthetic/nonpersonal data provenance, upload, see date range, unidentified buyers and unresolved products, then open findings. Uploaded synthetic data gets the same explicit provenance treatment as the built-in example. A declaration helps enforce scope but cannot prove a workbook contains no personal data.

**Acceptance:** blocked/failed imports leave previous results intact; no guessed purchases fill gaps; coverage and source type survive navigation. This belongs inside Import because it governs the existing data flow.

### 2. Spending, goals and action scenarios — new Consumer goals page

**Brief:** every section 6 benefit; section 7 moderate budgeting/saving/nudges and excellent goals/behaviour change.

**Location:** add `src/needstate/consumer_goals.py` for calculations and one route in the existing `web/app.js`/`webapp.py`. Reuse canonical quantities, line totals, receipt totals, quality and buyer dates; link to existing receipt evidence. Do not create another ingestion or customer-resolution system.

**Experience:** select a synthetic persona; view observed monthly/category spending with coverage; choose a budget/goal and constraints; compare feasible changes such as reducing a discretionary category frequency. Show baseline, assumed saving range, tradeoffs and receipts used. Suppress price substitution advice without verified comparable pack sizes, quantities and availability. Let the persona keep/dismiss a suggestion and compare subsequent synthetic periods with the goal.

**Why separate:** financial goals serve a consumer task, distinct from the business findings list. Combine budget, savings and nudges here rather than three thin pages.

**Acceptance:** no double-counting receipt totals and line totals; incomplete weeks labelled; missing spending never treated as zero; unavailable alternatives do not become promised savings. Demonstrated scenario benefit is conditional, not proof an action caused savings.

### 3. Forecast support — extension of Consumer goals and existing customer evidence

**Brief:** section 7 level 2 “what happens next”; sections 3 repeat/change and 6 influence future spend.

**Location:** add `patterns/forecast.py`, using E1/E6 histories; expose forecast explanations within the goal page and relevant customer evidence. Reuse E7 experiment infrastructure for validation instead of another validation suite/page.

**Experience:** estimated next-period observed spend or replenishment window, a range, and “not enough history” when needed. A goal scenario can adjust purchase frequency and display assumptions separately from the baseline forecast.

**Acceptance:** chronological holdout evaluation against last-period/simple-repeat baselines; error and interval coverage; no future leakage in product/segment fitting. Partial purchase coverage limits the forecast to observed spending. Only call it predictive after performance is measured; prescription additionally requires feasible actions and outcome follow-up.

### 4. Switching, trial and promotion context — extension of Customer evidence

**Brief:** section 3 switching, new-product motivation and promotion response; section 5 competing brands/shopper strategy.

**Location:** extend `patterns/transitions.py` using category/brand metadata and `trends.py:brand_share_decomposition`; expose through existing `workspace.py` reports and `web/app.js:evidence`. Use current optional Customer Feedback fields for attributed synthetic explanations, not invented motives.

**Experience:** dated observed brand sequence within a category; distinguish first observed trial, repeated use of a new brand, continued mixed buying and insufficient history. Adjacent promotion badges explain known labels and missingness. Show a descriptive within-retailer comparison only if comparable promoted/non-promoted records actually exist; otherwise explain that response cannot be estimated.

**Acceptance:** unknown brands, irregular histories and multiple brands per trip do not become switches; category growth is not credited entirely to a brand; retailer labels are not treated as causal discounts. Trial reasons remain unknown unless explicitly supplied as permitted feedback. This belongs beside the customer timeline because it explains that same history.

### 5. Business action briefs — extension of Findings and Exploratory observations

**Brief:** section 5 faster decisions, innovation, portfolio/category/shopper strategy and SKU rationalisation; section 7 consultancy-grade/prescriptive insights.

**Location:** extend the existing findings detail with an action-brief component in `web/app.js`; add `decision_briefs.py` to assemble existing E5/E8/E9 evidence. Link discovery candidates to existing review storage, rather than recreating the queue. Reuse portfolio exposure and brand/category decomposition.

**Experience:** a finding opens “Decision to investigate”: target outcome, affected cohort, evidence, competing explanations, two feasible options, required commercial inputs and experiment measure. For example, evaluate a complementary-product offer only as an experiment hypothesis, not inferred causal uplift. An innovation brief records the repeated need, coverage gap and research question.

**SKU boundary:** show a rationalisation research shortlist only when SKU identity is reliable. Family counts cannot justify discontinuing a SKU. Require margin, availability, substitution and category coverage inputs before estimating removal impact; expose assumptions and abstain otherwise.

**Acceptance:** every recommendation names its evidence and missing inputs; no invented margin, elasticity or ROI. Measurable experiment outcomes separate useful prescription design from proven commercial effectiveness. Keep this inside existing findings because actions should remain attached to their evidence.

### 6. Explainable behavioural segments — extension of Findings filters/action briefs

**Brief:** section 5 discover groups/consumer segmentation; section 7 excellent segmentation.

**Location:** extend `patterns/routines.py` and `workspace.py` to aggregate existing routine/category histories into named behavioural groups; add filters and small segment summaries to the current findings/action brief UI.

**Experience:** compare established category repeaters, newly observed buyers and changing-frequency buyers across categories, with sizes, coverage and overlaps. These are observed behaviour groups, not demographic or household identities.

**Acceptance:** declare whether groups overlap; freeze definitions before measuring future outcomes; check stability with held-out periods and missing-data simulations. Use an action-relevant segment only when it changes the proposed decision. No separate page or opaque clustering is necessary initially.

## C. Reconsideration/replacement threshold

**No feature replacement is justified by this brief.** Keep the current single-file import, missions, findings/exploratory separation and evidence pages.

Two targeted corrections meet the concrete-conflict threshold without replacing features:

1. **Data scope/provenance:** arbitrary workbook import has no permitted-data declaration, and uploaded synthetic data is not identified by the demo-only sample flag. That conflicts with the explicit section 4 restriction and risks misleading demo provenance. Extend Import as in proposal 1; local execution alone is insufficient.
2. **Continuity claims:** the single-file replacement workflow does not accumulate prior files or survive restart. It can satisfy continuous analysis only when users supply cumulative history. Explain that requirement and observed coverage; add persistence later only if needed. Do not claim missing receipts have been reconstructed.

Other limits are gaps to extend, not reasons to rewrite working features. In particular, historical mission inference should retain its useful role while being described accurately as interpretation rather than a forecast.

## Delivery and review boundary

This document completes the requested audit and proposal stage. Implementation is intentionally not started. For a 24-hour submission, prioritise a complete synthetic-persona journey: import → spending evidence → one goal → conditional action → follow-up measure, alongside one business action brief. Then add validated forecasts and richer segments if time/data permit. Do not claim excellent-level realised outcomes solely because a recommendation screen exists.
