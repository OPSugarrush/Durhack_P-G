import plotly.express as px
import streamlit as st

from _common import page, require_analysis, show_df, show_plot, synthetic_banner

page("Data Audit and Product Resolution", "🔎")
an = require_analysis()
synthetic_banner(an)
pl = an.pipeline

st.subheader("Reconciliation")
a = {k: v for k, v in pl.audit.items() if k != "missingness"}
cols = st.columns(len(a))
for col, (k, v) in zip(cols, a.items()):
    col.metric(k.replace("_", " "), f"{v:,}")
st.caption("Missingness (share of rows): " + ", ".join(f"{k}={v:.1%}" for k, v in pl.audit["missingness"].items()))
st.caption("Null promotion = UNKNOWN, never 'not promoted'. Promotion labels are retailer loyalty IDs, so promotion and retailer are confounded.")

st.subheader("Entity resolution: variant string -> product family")
cat = pl.resolution.catalogue
st.write(f"{pl.resolution.variant_map.shape[0]} raw strings -> **{len(cat)} families**. Deterministic merges only; fuzzy matches go to review.")
show_df(cat[["family_id", "family_name", "n_variants", "n_lines", "confidence", "variants"]].assign(variants=lambda d: d["variants"].map(" | ".join)))
if len(pl.resolution.review_pairs):
    st.warning("Near-duplicate families awaiting human review (never auto-merged).")
    show_df(pl.resolution.review_pairs)

st.subheader("Hierarchy: variant > family > brand > function > category > department")
h = pl.hierarchy.fillna({"brand": "(no brand)", "owner": "(unassigned)"})
fig = px.treemap(h, path=["department", "category", "function", "brand", "family_name"], maxdepth=4)
fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0))
show_plot(fig)
show_df(h)
