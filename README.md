# NeedState — customer intelligence workspace

A local, conclusion-first workspace for understanding what customers repeatedly buy, what changes, and whether that change is shared across customers. The primary application is now a custom responsive web interface with a Python analysis service. No paid API is required.

## Start

On this machine, double-click **Start NeedState.cmd**, then open http://127.0.0.1:8502.

For a fresh checkout (Python 3.11+):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,web]"
.\.venv\Scripts\python.exe -m needstate.workspace.server
```

Upload your workbook on **Receipt data**. To enable the sample button, place the supplied workbook at `data/raw/DH_Synthtic_Receipt_Database.xlsx`. Data files are intentionally excluded from Git.

## The workflow

1. **Start here** explains the purpose and how to interpret a finding.
2. **Receipt data** previews workbook sheets and columns before import. Add receipts to the current dataset or explicitly replace it. Identical receipts are skipped; conflicting receipts stop the import without altering the current dataset. Synthetic and real sources cannot be combined.
3. **Findings** leads with what changed, how many shopping trips it represents, and what a company could investigate next. Filter category or shopping function, strength of evidence, and P&G relevance. Technical evidence is available inside each finding.
4. **Customers** distinguishes established routines, newly observed purchases, purchases no longer observed, and changes in frequency. Follow a customer through to the individual receipts behind the interpretation.

Imports accept XLSX and CSV with these required headers: **Receipt ID, Consumer ID, Date, Product Name**. Download the template in the app for all supported fields, including quantities, prices, retailer and line numbers. Limits: 30 MB per upload and 150,000 combined product rows. The first 20 workbook sheets are previewed.

## How the evidence works

The observation window is divided into earlier and recent periods. Customer comparisons require at least three receipts in each period. Population changes compare the same customers across both periods, giving each customer equal weight. They include eligible non-buyers, rather than selecting only customers who purchased a category.

Customer evidence labels reflect receipt quality, observation length and receipt coverage. They are transparent history measures, **not probabilities of intent or future purchases**. Population findings use customer bootstrap intervals, directional tests, and false-discovery correction separately across category and function comparisons. Supported changes also require minimum customer and buyer coverage. The interface explains the meaning before showing technical values.

Monthly charts are descriptive and can contain different customer mixes. Absence from observed receipts does not prove abandonment. Leading-brand changes are observations, not proof of substitution. Retailer coverage, short histories, synthetic provenance and unavailable seasonal comparisons are surfaced where relevant. The engine does not invent trends when evidence is weak.

The taxonomy and portfolio lens are configurable under `configs/`. Unknown products remain visibly unclassified. Added rules cover more personal care, baby care, pet care and food functions; this is still a seed taxonomy rather than universal product recognition.

## Team handoff

This redesign is developed on `feature/customer-intelligence-workspace`, leaving `main` intact. Teammates can keep working on their existing branches and review or merge this branch when ready. Avoid resetting or force-pushing shared branches.

Main code areas:

- `web/`: browser interface, styles and navigation; no frontend build step.
- `src/needstate/workspace/`: import validation, customer/population reports and local service.
- `configs/`: taxonomy, portfolio and pipeline settings.
- `tests/test_workspace.py`: import safety and customer analysis checks.

The previous Streamlit interface and original analysis modules remain available for compatibility. Launch it separately with `python -m streamlit run app/Home.py`. Its older methodology documents describe that analytical workbench; they are not a specification of the new web screens.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
# With the local service running:
.\.venv\Scripts\python.exe scripts/verify_workspace_api.py
```

`scripts/verify_web.cjs` exercises the real browser journey with Playwright and Edge when Playwright is installed. It saves local screenshots under `data/web-preview/`.

## Local research scope

Datasets are held in browser-specific server sessions in memory and expire after inactivity or server restart. Export findings before closing your work; this is not persistent storage. The service binds to localhost. Do not expose it as a public production service without authentication, durable storage and deployment hardening. Synthetic sample discoveries do not validate real-world consumer behavior.
