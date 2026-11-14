# NeedState Engine

A local Streamlit app for exploring receipt patterns, product families and observed consumer routines. Based on the supplied Claude build, completed as a reusable hackathon foundation. All interpretation is a research hypothesis; scores are uncalibrated rules, not probabilities of consumer motivation.

## Start on Windows

Dependencies and the supplied workbook are already installed in this workspace:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/Home.py
```

Or double-click `Start NeedState.cmd`. Open the local address printed by Streamlit. The initial consumer-adjusted analysis is cached and can take several minutes.

For a fresh checkout with Python 3.11 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m streamlit run app/Home.py
```

Copy the source workbook into `data/raw/DH_Synthtic_Receipt_Database.xlsx`, or upload an XLSX/CSV in the sidebar. Raw data and review decisions are excluded from version control. The original Downloads workbook is unchanged.

## What is implemented

- XLSX/CSV adapters and YAML field mappings, canonical lines and receipt integrity checks.
- OCR folding, abbreviation expansion, unique-prefix resolution, fuzzy review suggestions and nullable brand/owner metadata.
- Product hierarchy and configurable portfolio exposure/adjacency. Empty owners and brands select general-market mode.
- Consumer-adjusted prevalence changes with multiple-test correction, minimum detectable effect estimates and seasonality warnings.
- Binary fixed-margin co-purchase randomisation within each consumer. Receipt sizes and personal product counts remain fixed. Consumer bootstrap intervals are explicitly for **pooled lift**.
- Observed concentration/repeat routines, graph basket decomposition, independent need scores, supporting products, abstention and remove-product sensitivity.
- Exploratory discovery and local transactional review decisions; approving a candidate does not silently change the taxonomy.
- Trend/bundle injections, shuffled-null experiments and missing-data degradation experiments.
- Eight dashboard pages, CSV exports and an offline evidence narrator. No paid API or model download required.

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

`configs/pipeline.yaml` selects the data, mapping, taxonomy, seed and lens. All paths are relative to the project root of that config. `configs/mappings/generic_csv.yaml` demonstrates a second schema. Upload a mapping alongside a new data file to keep the analytics unchanged. Declare synthetic provenance in the sidebar or config.

The workbook taxonomy is a seed, not universal product knowledge. Unknown brands remain null and unknown functions remain unclassified. A brand may span functions/categories, so brand is an attribute rather than a strictly nested node in the statistical testing tree. Category → family is the implemented parent-gated drilldown.

## Scientific limits

See [verified results](docs/RESULTS.md), [methodology](docs/METHODOLOGY.md), [architecture](docs/ARCHITECTURE.md), and [demo guide](docs/DEMO.md). In particular, the app does not guarantee zero organic flags, identify seasonality from six months, estimate a causal promotion effect, recover whole missing receipts or validate real shopper intentions. No labelled intention data exists. Missing-data agreement measures stability against the clean baseline, not truth.

This is a local research foundation. Authentication, multi-user isolation, deployment hardening, survey validation, calibrated learning and automatically promoted taxonomies are future work.
