import plotly.express as px
import streamlit as st

from _common import family_names, page, require_analysis, show_df, show_plot, synthetic_banner

page("Consumer Routines", "🔁")
an = require_analysis()
synthetic_banner(an)
names = family_names(an)
s = an.routines_summary

st.write("The real signal in receipt data is often **consumer-level routine**, a different unit from basket-level missions. Observed repeat behaviour only; nothing about households, health or life stage is inferred.")
c = st.columns(4)
c[0].metric("Pooled concentration (HHI)", f"{s['pooled_hhi']:.4f}")
c[1].metric("Mean consumer concentration", f"{s['mean_consumer_hhi']:.4f}")
c[2].metric("Concentration ratio", f"{s['concentration_ratio']:.1f}x")
c[3].metric("Share of a consumer's products bought 2+ times", f"{s['mean_repeat_entity_share']:.0%}")
show_plot(px.histogram(an.routines, x="hhi", nbins=40, title="Distribution of consumer concentration (pooled HHI is the benchmark)"))

st.subheader("Repeat rate by product family")
from needstate.patterns.routines import repeat_rates
from needstate.patterns.transitions import entry_exit
level = st.selectbox("Routine hierarchy level", ["family", "brand", "function", "category"])
r = repeat_rates(an.baskets[level])
if level == "family":
    r["entity"] = r["entity"].map(lambda x: names.get(x, x))
show_df(r.round(3))
st.subheader("Entry and exit in consecutive observed baskets")
st.caption("Observed presence changes only. A missing next purchase does not establish abandonment or substitution.")
show_df(entry_exit(an.baskets[level]).round(3))

st.subheader("One consumer's routine")
cid = st.selectbox("Consumer", sorted(an.routines["customer_id"].dropna().unique()))
lines = an.pipeline.lines[an.pipeline.lines["customer_id"] == cid]
freq = lines.groupby("family_id")["transaction_id"].nunique().sort_values(ascending=False).head(15)
fig = px.bar(x=freq.values, y=[names.get(f, f) for f in freq.index], orientation="h", labels={"x": "receipts containing product", "y": ""})
fig.update_layout(yaxis=dict(autorange="reversed"))
show_plot(fig)
