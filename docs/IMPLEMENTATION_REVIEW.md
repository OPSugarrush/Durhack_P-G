# Review notes: additive consumer value

Base: teammate commit a288724. Branch: audit/hackathon-brief-gap-review. Nothing pushed.

Implemented:
- Existing Import requires a synthetic-data declaration, enforced by the HTTP endpoint. Uploaded findings are labelled synthetic. The single-file replacement workflow is unchanged and now explains cumulative history.
- One Spending & goals page uses the existing processed receipt data. It shows per-buyer monthly/category spending and price coverage, plus a target/reduction scenario. It never adds receipt totals to item totals, and suppresses scenario results for incomplete price coverage.
- Each existing finding detail has an expandable action brief: a proposed investigation, comparison option, outcome measure and limits. Existing behaviour cohorts are identified as overlapping groups, not demographics.

Organisation: financial aggregation is in consumer_goals.py; its UI is in web/goals.js; existing workspace processing supplies the data without a second pipeline run. Existing navigation and evidence drill-down are retained.

Deliberately deferred after implementation review:
- Forecasts: temporal validation and sufficient histories are needed before offering a future estimate. The new calculation is explicitly a conditional scenario.
- Automated SKU/portfolio decisions: reliable SKU, margin and substitution inputs are absent. Action briefs state the required inputs.
- Brand switching and promotion response: a credible sustained-switch model and comparable promotion observations need more work; no substitution or causal response is fabricated.
- Persistent goals and long-term engagement: current server data is session-only; goal controls are visit-only. No claim of measured behaviour change.
- New segmentation model: current behaviour cohorts already serve the immediate filtering task. Avoid a parallel segment system until an action requires one.

The import declaration is a scope guard, not a personal-data detector. This implementation deliberately restricts the demo upload path to synthetic receipts. Permitted public nonpersonal sources would need explicit provenance support later.

Spending limitations: nonnegative finite item totals only; refunds and missing values are excluded and counted in coverage. Currency is inherited from the workbook; no conversion is attempted. No inference fills missing trips. The latest recorded month can be partial. Scenario reduction is user-specified and assumes unchanged prices, coverage and no replacement spending.

Review using Start NeedState.cmd (port 8765): Explore example, open Spending & goals, change buyer/target/reduction, then open any finding and expand its action brief. Import requires the synthetic-data checkbox. Refreshing or moving away resets goal controls.
