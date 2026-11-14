# Methods and limits

## Identity and quality

The supplied data has synthetic OCR-like 0/O and 1/I substitutions. Normalisation folds these symmetrically, expands configured phrases and merges uniquely extending long prefixes. This assumption is appropriate for the supplied generator but requires review on real catalogues, especially product codes and sizes. Fuzzy candidates are never automatically merged. Entity confidence values are heuristic provenance markers, not empirically calibrated match probabilities. Family IDs derive from normalised family keys and are stable against frequency changes; newly supplied longer truncation completions can change a key.

Missing product names stay as unresolved lines so the quality report can show their loss. Missing promotion labels remain unknown. Receipt quality combines observed resolution, arithmetic and price checks; a missing total is not reported as a successful reconciliation. Completeness is only an observed-evidence proxy: an internally consistent receipt can still omit an item or a whole shop.

## Trends and multiplicity

The trend statistic correlates binary receipt presence with calendar month. Null moments are calculated exactly for month labels permuted within a consumer; the reported two-sided p-value uses a **normal approximation** to those moments. Optional Monte Carlo p-values validate that approximation. Sparse products, consumer entry/exit, retailer assortment and changing basket sizes remain limitations. The direction/slope describes pooled observed prevalence, while the test conditions on consumer identity.

BH adjusts each standalone hierarchy-level scan. Parent-gated category → family results use root BH and global Bonferroni across all descendants, counting them before parent selection. This is conservative descendant family-wise control, not a claim that applying BH to pooled selected children establishes hierarchical FDR. Exploration across several levels remains several analysis families.

Minimum detectable relative increase is a two-proportion normal planning calculation with nominal alpha .05 and 80% power. It uses the first/last halves' receipt counts. It does not include clustering, multiplicity or seasonal effects and is not a filter for accepting/rejecting a realised result. Injection recovery is the more relevant empirical detection-floor demonstration. One month cannot support change testing. Two annual cycles are required even to mark seasonality as assessable; the baseline does not fit a seasonal model.

## Associations and routines

Co-purchase uses binary receipt incidence. Within each consumer, Curveball trades redistribute exclusive products between two receipts while preserving every receipt size and every personal product frequency. A fixed burn-in and thinning generate the null. Duplicates cannot collapse because every receipt remains a set. Chains can mix slowly in constrained consumers, so seed sensitivity and longer runs matter.

One-sided Monte Carlo p-values use `(1 + exceedances)/(draws + 1)`. BH includes **all possible product pairs** before display support filtering. Finite resolution makes this conservative for isolated discoveries among thousands of tests; an empty discovery queue is valid. Larger `n_perm` improves resolution at a runtime cost. No approximate normal association p-value is substituted to manufacture discoveries.

Adjusted lift is observed pair count / mean null pair count. Consumer bootstrap intervals resample complete consumer histories and describe **pooled lift only**. They are not uncertainty intervals for adjusted lift. Missing customer IDs get unique singleton receipt blocks; they cannot create artificial shared-consumer evidence. Routine summaries exclude unknown IDs. Repeat rates require at least three observed receipts; observation-window censoring remains.

## Inference, review and validation

Basket graphs combine configured functional similarity with supported associations. Communities are candidate product groupings, not verified shopping missions. Each need has an independent heuristic support/purity score within its partition. Evidence concentration, observed quality and model score remain separate. An unrelated item is not genuine contradictory evidence: `contradictory_evidence` remains empty unless an actual contradiction is established, while `other_partition_products` lists unrelated supporting-context items. Alternative explanations are explicit.

Discovery produces exploratory communities only when corrected pair evidence exists. Temporal/consumer/retailer replication and human validation remain visibly unverified. Approvals are audited research decisions and require an explicit config edit before reuse as taxonomy. The narrator describes products/functions and suggests follow-up research; it does not call an association an unmet need.

Injected lines live only in experimental copies and carry `injected=True`. Trend recovery tests added prevalence ramps; bundle recovery tests an emerging pair-indicator prevalence change. Neither validates genuine consumer intent or all forms of co-purchase change. Shuffled-null scans estimate false alarms under the declared null, not a guarantee of zero false positives. Synthetic generator recovery validates mechanics rather than real-world consumer understanding.

Missingness experiments compare clean and corrupted copies: MCAR lines/receipts/names/prices/IDs, retailer-conditional MAR, preferential price/category loss MNAR, OCR noise and duplication. Match purity/fragmentation are relative to the clean resolver, not manual identity truth. Need agreement is stability against baseline rules, not accuracy. Trend flags after corruption are flags, not automatically false alarms. Whole missing receipts reduce coverage and are never reconstructed.

Promotions are confounded with retailer labels in this workbook and unlabelled lines are unknown. The app therefore estimates no causal promotion effect. Population representativeness, sensitive characteristics, actual motivation, demand and market size are outside the evidence.
