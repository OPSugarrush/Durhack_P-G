# NeedState Engine

NeedState turns receipt spreadsheets and photos into evidence for business decisions: which categories reach shoppers, where purchasing is changing, which brands deserve attention, and what opportunities merit investigation. Built for the P&G challenge at DurHack, it supports a configurable company portfolio lens.

The primary application is a local browser workspace backed by Python. Company analysts can move from category and brand insights to forecasts and the receipt histories supporting each finding. Basket mission scores remain explainable suggestions, not measured probabilities of shopper intent.

## Start on Windows

Double-click **Start NeedState.cmd** or run the following from the checkout:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ocr]"
.\.venv\Scripts\python.exe -m needstate.webapp --open
~~~

Requires Python 3.11 or newer. The workspace runs at [localhost:8765](http://127.0.0.1:8765). After installation, double-click **Start NeedState.cmd** to launch it again. Keep the server running while using the app; press Ctrl+C in its terminal to stop it. Add `--port 8766` to the launch command if the default port is occupied. For spreadsheet-only use, install `".[dev]"` instead; the `ocr` extra enables receipt image processing. No paid API key is required.

## Using the workspace

1. Load the built-in synthetic example or open **Data** to import a spreadsheet or receipt photo. For photos, generate a customer ID or enter an existing one and review the extracted items.
2. Choose **Add to my data** to combine the upload with the current collection, or **Focus on this upload** to analyse it separately.
3. Open **Opportunities**: **Category overview** shows reach and purchasing changes; **Business priorities** highlights investigation candidates; **Forecasts** shows available outlooks and portfolio estimates.
4. Open **Brands** for the brand overview, business priorities and switching histories. Use **Explore** to inspect supporting shopping patterns and receipt evidence.

A single receipt can support a receipt summary but cannot establish a longitudinal trend. Imported data and reviews are held in server memory and are cleared when the server restarts. This is a local research workspace.

## Import format

Use one row per purchased item and the headers in [the receipt mapping](configs/mappings/dh_synthetic_receipts.yaml). Keep receipt and buyer IDs as Excel text to preserve leading zeros. Exact numbered lines and repeated receipts are counted once. Conflicting overlaps reject the complete batch. Without line numbers, repeated items within a receipt are preserved. Workbooks are limited to 16 MB.

## What is implemented

### Company opportunities and forecasts

Category and brand views connect observed reach, purchasing movement and repeat histories to business investigation priorities. Portfolio analysis uses configured brand/owner metadata, including P&G where recognised. Unknown brands remain unclassified.

Portfolio forecasts estimate inclusion on the next **observed category trip**, conditional on another trip occurring. They require sufficient history and are compared with a baseline on a held-out period. They do not predict revenue or the return from marketing investment. Experiment economics use analyst-supplied assumptions. See [portfolio decisions](docs/PORTFOLIO_DECISIONS.md) for requirements and limitations.

### Reviewing shopping missions

The interactive workspace compares product pairings among each buyer's trips with the same number of distinct product families. A pairing can strengthen the graph if it qualifies in both halves of the date range. Each half requires at least four observed pairings, three expected, positive excess for two buyers, adjusted lift of 1.25, and a corrected one-sided approximate test at 0.05. Sparse data often support only a category-based suggestion. A department match alone cannot join items in the workspace.

For a blind human review, run `python -m needstate.mission_review receipts.xlsx annotations.csv`. This writes a reproducible sample with one row per product. Within each receipt fill in a group identifier and enter the mission labels for that group in **needs**, separated by a vertical bar. Leave needs empty for a group with no clear purpose. Use labels from `configs/need_states.yaml`. Run the same command with `--compare` to see product-pair agreement, exact label agreement and the specific disagreements for rule review.

Workbook columns named **Pack Size**, **Format**, **Ingredients** and **Customer Feedback** appear alongside matching products when supplied.

- XLSX/CSV adapters and YAML field mappings, canonical lines and receipt integrity checks.
- OCR folding, abbreviation expansion, unique-prefix resolution, fuzzy review suggestions and nullable brand/owner metadata.
- Product hierarchy and configurable portfolio exposure/adjacency. Empty owners and brands select general-market mode.
- Consumer-adjusted prevalence changes with multiple-test correction, minimum detectable effect estimates and seasonality warnings.
- Binary fixed-margin co-purchase randomisation within each consumer. Receipt sizes and personal product counts remain fixed. Consumer bootstrap intervals are explicitly for **pooled lift**.
- Observed concentration/repeat routines, graph basket decomposition, independent need scores, supporting products, abstention and remove-product sensitivity.
- Exploratory discovery and local transactional review decisions; approving a candidate does not silently change the taxonomy.
- Trend/bundle injections, shuffled-null experiments and missing-data degradation experiments.
- The primary browser workspace, plus the legacy Streamlit research pages, CSV exports and an offline evidence narrator. No paid API or model download required.

## Commands

With the package installed, use:

```powershell
python -m needstate audit
python -m needstate analyse
python -m needstate validate --quick
python -m needstate missing-data --quick
python -m pytest -q
```

Without an editable install, set `$env:PYTHONPATH='src;.'` before these commands. Full missingness grids are deliberately expensive; select a few conditions in the app first.

## Configuration and reuse

The main browser UI lives in `src/needstate/web` and is served by `needstate.webapp`. Shared analysis lives in `src/needstate`, OCR extraction in `receipt_ingestion`, and automated checks in `tests`. The Streamlit pages under `app` are a separate legacy research interface.

`configs/pipeline.yaml` provides the shared default for data, mapping, taxonomy, seed and lens. For machine-specific settings, copy it to `configs/pipeline.local.yaml`; the app prefers that local file when present, and it is excluded from Git. All paths are relative to the project root. `configs/mappings/generic_csv.yaml` demonstrates a second schema. Upload a mapping alongside a new data file to keep the analytics unchanged. These sidebar and custom mapping options belong to the legacy Streamlit app (python -m streamlit run app/Home.py).

The workbook taxonomy is a seed, not universal product knowledge. Unknown brands remain null and unknown functions remain unclassified. A brand may span functions/categories, so brand is an attribute rather than a strictly nested node in the statistical testing tree. Category → family is the implemented parent-gated drilldown.

## Scientific limits

See [verified results](docs/RESULTS.md), [methodology](docs/METHODOLOGY.md), [architecture](docs/ARCHITECTURE.md), and [demo guide](docs/DEMO.md). In particular, the app does not guarantee zero organic flags, identify seasonality from six months, estimate a causal promotion effect, recover whole missing receipts or validate real shopper intentions. No labelled intention data exists. Missing-data agreement measures stability against the clean baseline, not truth.

This is a local research foundation. Authentication, multi-user isolation, deployment hardening, survey validation, calibrated learning and automatically promoted taxonomies are future work.
