import pandas as pd
import plotly.express as px
import streamlit as st

from _charts import mission_graph
from _common import family_names, page, require_analysis, show_df, show_plot, synthetic_banner
from needstate.need_state.inference import predict_basket

page("Basket Explorer: Missions and Need-States", "🧺")
an = require_analysis()
synthetic_banner(an)
pl = an.pipeline
names = family_names(an)

multi = pl.lines[pl.lines["owner"].notna()].groupby("transaction_id")["family_id"].nunique()
mixed = pl.lines[pl.lines["department"] == "home_personal_care"].groupby("transaction_id")["category"].nunique()
mode = st.radio("Pick from", ["Baskets with 3+ home and personal care categories", "Baskets with 2+ portfolio products", "Any receipt"], horizontal=True)
ids = {"Baskets with 3+ home and personal care categories": list(mixed[mixed >= 3].index),
       "Baskets with 2+ portfolio products": list(multi[multi >= 2].index)}.get(mode, list(pl.quality.index))
tid = st.selectbox("Receipt", ids[:500])
if tid is None:
    st.info("No receipts match this filter. Choose Any receipt.")
    st.stop()

g = pl.lines[pl.lines["transaction_id"] == tid]
fams = list(g["family_id"].dropna().unique())
mconf = pl.lines.drop_duplicates("family_id").set_index("family_id")["match_confidence"].to_dict()
pred = predict_basket(tid, fams, pl.hierarchy, pl.config.need_states, float(pl.quality.loc[tid, "data_completeness"]), mconf,
                      assoc=an.pairs[an.pairs["q"] < 0.05])

left, right = st.columns([1, 1])
with left:
    st.subheader("Receipt")
    show_df(g[["line_number", "raw_product_text", "family_id", "category", "quantity", "unit_price"]])
with right:
    st.subheader("Mission decomposition")
    show_plot(mission_graph([p for p in pred.mission_partitions], names, pl.hierarchy, None))
    st.caption("Diamonds = ambiguous products (comparable pull toward another mission). Not force-assigned.")

st.subheader("Candidate need-states (independent scores, never normalised)")
if pred.candidate_needs:
    cand = [{"need": c["label"], "mission": c["partition_id"], "score": c["score"],
             "supporting": ", ".join(names.get(f, f) for f in c["supporting_product_ids"]),
             "other partition products": ", ".join(names.get(f, f) for f in c["other_partition_products"])} for c in pred.candidate_needs]
    import pandas as pd
    cdf = pd.DataFrame(cand)
    show_plot(px.bar(cdf, x="score", y="need", color="mission", orientation="h", range_x=[0, 1]))
    show_df(cdf)
else:
    st.warning("No need-state in the taxonomy is supported by this basket.")

c = st.columns(4)
c[0].metric("Data completeness", f"{pred.data_completeness:.2f}")
c[1].metric("Evidence concentration", f"{pred.evidence_concentration:.2f}", help="Top-two margin. Low = diffuse. Does not alter any score.")
c[2].metric("Heuristic model score", f"{pred.model_confidence:.2f}", help="Uncalibrated rule score; not a probability of consumer intent.")
c[3].metric("Abstained", "yes" if pred.abstained else "no")
st.caption("Three separate quantities on purpose: candidate_needs (genuine plural intents), prediction uncertainty, and data completeness.")
st.caption("Alternative explanations include replenishment, unrelated purchases and purchases for several people. Other products are not evidence against a need. Receipt completeness cannot reveal unrecorded whole receipts.")

if pred.candidate_needs:
    st.subheader("Sensitivity (not causal)")
    prod = st.selectbox("Remove product and re-score", fams, format_func=lambda f: names.get(f, f))
    alt = predict_basket(tid, [f for f in fams if f != prod], pl.hierarchy, pl.config.need_states, pred.data_completeness, mconf,
                         assoc=an.pairs[an.pairs["q"] < 0.05])
    before = {c["need_state_id"]: c["score"] for c in pred.candidate_needs}
    after = {c["need_state_id"]: c["score"] for c in alt.candidate_needs}
    rows = [{"need": k, "before": before.get(k, 0.0), "after": after.get(k, 0.0), "change": after.get(k, 0.0) - before.get(k, 0.0)} for k in sorted(set(before) | set(after))]
    show_df(pd.DataFrame(rows).round(3))
