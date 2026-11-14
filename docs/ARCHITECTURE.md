# Architecture

The current user request governs this build. The original prompt and strategy document are historical design inputs; the latest confounder analysis supersedes their requests for seasonal adjustment and automatic fuzzy merges.

| Layer | Input | Output | Boundary |
|---|---|---|---|
| Ingestion | XLSX/CSV + field mapping | Canonical line table | Source column names stop here |
| Validation | Canonical lines | Reconciliation and per-receipt quality | Structural conflicts fail clearly; missing optional values remain missing |
| Product intelligence | Descriptions + configured vocabulary | Family map, hierarchy and review pairs | Fuzzy similarity never auto-merges |
| Basket intelligence | Enriched observed lines | Binary matrices, partitions, candidate need scores | No inferred items enter the observed ledger |
| Pattern discovery | Matrices and consumer blocks | Changes, adjusted associations, routine summaries, candidates | Basket and consumer units remain separate |
| Reliability | Evidence and experimental copies | Abstention, simulation metrics, review history | No calibrated probability or motivation accuracy claims |

`service.analyse` composes these layers. The command line and Streamlit pages share this service. Configurations are YAML; local review decisions use SQLite transactions. File upload stays in process memory. Cached analysis keys include source bytes, mapping bytes and source/config modification times.

Brand and owner are nullable portfolio attributes. A brand can serve several functions and categories; the hierarchy is therefore a graph rather than a universal linear tree. Statistical drilldown uses the unambiguous category → family path. Standalone family, brand, function and category scans are exploratory and each have their own correction family.

The reusable engine has no workbook row counts or brand assumptions embedded in analytical algorithms. Dataset-specific keywords and owner seeds live in `configs`. Source images are references only; no receipt images were supplied.

Extension points: authenticated deployment, richer multi-function catalogues, reviewed identity overrides, genuine proxy labels, retailer/time replication, consumer holdouts and optional LLM explanation. The offline narrator is intentionally sufficient for the demo; it does not invent statistical evidence.
