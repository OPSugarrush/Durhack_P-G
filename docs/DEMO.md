# Demo guide

## Primary browser application

Launch with `python -m needstate.webapp --open` after installing the project as described in the [README](../README.md).

1. Open **Data** and demonstrate reviewing an upload, then adding it to the collection or focusing on it separately. A single receipt demonstrates extraction, not forecasting.
2. Open **Opportunities → Category overview** for leading categories and purchasing changes. Distinguish popularity from growth.
3. Open **Business priorities** and inspect a supported investigation candidate. Follow its evidence before proposing a business action.
4. Open **Forecasts** and explain the available estimate. Portfolio repeat forecasts are conditional on a further observed category trip; sparse history may not support one.
5. Open **Brands** for the overview, business priorities and switching histories. Observed purchase sequences do not establish permanent switching.
6. Use **Explore** to connect findings to baskets and products.

State that demonstration receipts are synthetic. Frame opportunities as reasons to investigate or run a controlled test, rather than guaranteed investment returns. See [portfolio methodology](PORTFOLIO_DECISIONS.md).

## Legacy research walkthrough

The following refers to the separate Streamlit research pages and validation tools, rather than the primary browser navigation.

1. Open Overview and show the measured audit and family count. State that the receipts are synthetic.
2. Use Pattern Engine to distinguish raw nominal p-values from corrected results. Show seasonality as unassessable and the approximate power estimate beside each entity. Do not promise a completely empty organic scan.
3. Open Consumer Routines. Show personal concentration against pooled concentration, then the observed repeat purchases. This is a consumer-level observation, separate from a basket mission.
4. In Pattern Engine, compare pooled and adjusted co-purchase lift. The null preserves both personal frequencies and basket sizes. If no pair survives correction, show that result and the Monte Carlo resolution limitation.
5. In Basket Explorer, select a basket with several home/personal-care categories. Show partitions, product support, independent need scores and remove-product sensitivity. Explain that these are possible interpretations, not intent labels.
6. Run trend-recovery validation at several strengths. Explain added end-period percentage points versus relative growth and show recovery rates. Run shuffled-null scans independently. Bundle injection illustrates another pattern type.
7. Run a small Missing Data experiment. Contrast lost receipts with missing names/prices and show measured degradation/abstention. Missing whole receipts have no reconstructed contents.
8. Upload a differently named CSV with `generic_csv.yaml` to demonstrate the ingestion boundary. An empty portfolio lens selects general-market mode.

Commercial framing: the engine helps analysts decide which observed routines and patterns deserve further research. A possible P&G adjacency is a reason to design a follow-up study, not proof of a portfolio gap. A credible next step uses genuine retailer data, survey/proxy labels and held-out consumers/time/retailers.
