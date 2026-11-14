# Verified results on the supplied workbook

The original workbook was copied into `data/raw`; the Downloads source was not edited. The saved experiment tables live in `data/processed`. Values below describe synthetic data and the stated tests, not market findings.

| Measure | Observed result |
|---|---:|
| Line items | 32,776 |
| Receipts | 3,005 |
| Consumer IDs | 300 |
| Raw descriptions | 210 |
| Resolved families | 99 |
| Line arithmetic mismatches | 0 |
| Receipt total mismatches | 0 |
| Duplicate source rows | 0 |
| Missing promotion labels | 80.5% |
| Consumer/pooled concentration ratio | 3.59 |
| Family trend flags after within-level BH | 1 / 99 |
| Supported co-purchase pairs passing BH | 116 / 4,422 displayed pairs |
| Shuffled trend-null scans with any flag | 0 / 10 |

Co-purchase used seed 42 and 999 fixed-margin Curveball draws. BH counted all 4,851 possible pairs before the minimum-eight support display filter. The p-value floor is .001, and many flags are tied at that floor. Counts can change across seeds and longer chains; this is exploratory evidence requiring replication. Bootstrap intervals in the export describe pooled lift only.

The single family flag is Carte D'Or vanilla ice cream (approximate p=.00044, q=.0436). Its increase is not proof of an emerging consumer need; seasonality is unassessable and sparse-event normal approximation deserves scrutiny. Four category flags also appear; changing observed basket size is a material alternative explanation. The app shows that context rather than suppressing these results to force a zero-trend story.

| Injected end-period prevalence ramp | Recoveries | Rate |
|---|---:|---:|
| +1 percentage point | 0 / 12 | 0% |
| +2 percentage points | 0 / 12 | 0% |
| +4 percentage points | 1 / 12 | 8.3% |
| +8 percentage points | 8 / 12 | 66.7% |

These are small experiments across selected families and injection seeds. They show limited power, not a universal detection guarantee. Zero false-alarm scans out of ten also has substantial uncertainty.

The missing-data verification ran five conditions at 10% and 30%, using 60 sampled receipts for need-score stability. At 30% blank names, baseline top-need agreement was about 67.8% and abstention rose from 13.3% to 44.1%. Dropping 30% of whole receipts retained about 70.1% of receipt coverage; remaining-receipt agreement was 100%, which says nothing about the invisible receipts. No reconstruction was attempted.

The fuller UI grid additionally supports retailer-conditional loss, price-selective loss, category-selective loss, OCR changes and duplicate lines. These are implemented scenarios; the saved ten-condition study does not claim to validate every one.

Verification completed locally: 34 automated tests passed, all eight actual Streamlit pages executed without exceptions, the false-alarm button completed, and the running local server returned a healthy response. Page execution checks used nine randomisations for speed; the saved association results above used the full 999-draw configuration. Visual browser inspection and production deployment were not part of these checks.
