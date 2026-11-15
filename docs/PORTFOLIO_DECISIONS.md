# Company opportunity workflow

The landing page is Opportunities, with a P&G default lens and optional whole-market context. The existing interface styling, imports, category evidence and brand histories are retained. Shopper budgeting is no longer a primary navigation destination.

The company forecast estimates P&G inclusion on the next observed category trip, conditional on another observed trip. It is not a calendar-time spending forecast or a prediction of intervention uplift. At least three training months, two training category trips per buyer and 20 held-out buyers are required. The latest observed month supplies one held-out next trip per eligible buyer. A smoothed shopper-history baseline is compared with the category baseline using Brier error; the selected approach is refitted to available history. This single holdout is preliminary validation, not repeated out-of-time validation or calibration certification.

Opportunity candidates show observed sequences of two portfolio purchases followed by two non-portfolio purchases. These are investigation candidates, not proven switching or causal losses. Unknown-brand receipts are excluded from this comparison; recognised-brand coverage is disclosed. Portfolio categories use the existing hierarchy's P&G ownership mapping, which is incomplete and must be extended only with verified metadata.

The experiment brief records the report version, observed cohort, conditional forecast, user-entered audience/cost/contribution, break-even improvement and a controlled-test outline. Monetary inputs must use a common currency. No manufacturer profit or intervention response is inferred from shelf spending.

Import preparation now recovers blank customer, retailer and date metadata only from an unambiguous existing receipt group. Missing receipt identities, wholly undated receipts, conflicting metadata and partially numbered lines still require correction. This release does not yet implement a quarantine/review workflow, recovery provenance export, analysis-specific eligibility for undated data, recommendation robustness simulations, or spending forecasts. Those remain subsequent work; existing missing-data research utilities are not represented as integrated decision validation.

Validation: targeted opportunity, metadata recovery, existing business comparison and upload tests; JavaScript syntax checks. No new visual-browser validation is claimed.
