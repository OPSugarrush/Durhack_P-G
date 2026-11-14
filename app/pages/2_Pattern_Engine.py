import plotly.express as px
import streamlit as st

from _charts import monthly_prevalence
from _common import family_names, get_level_pairs, lens_sidebar, page, require_analysis, show_df, show_plot, synthetic_banner
from needstate.patterns.trends import brand_share_decomposition

page("Pattern Engine", "📈")
an = require_analysis()
synthetic_banner(an)
lens = lens_sidebar(an)
pl = an.pipeline
names = family_names(an)

t_trend, t_hier, t_pairs, t_brand = st.tabs(["Trends", "Hierarchical FDR", "Co-purchase (within-consumer null)", "Brand: category vs share"])

with t_trend:
    st.caption("Prevalence change is not proof of an emerging need. Retailer assortment, basket size and seasonal effects can still explain a flag.")
    level = st.selectbox("Hierarchy level", ["category", "function", "brand", "family"], index=3)
    df = an.trends[level]
    st.caption(f"Seasonality: {df['seasonality'].iloc[0]}" if len(df) else "No entities have sufficient support.")
    st.caption("`mde_relative` = smallest relative change detectable (80% power) with the data in each half; an approximate independent-receipt planning estimate, before multiplicity and consumer clustering. It is not a decision threshold.")
    only_sig = st.checkbox("Only significant (FDR)", value=False)
    view = df[df["significant"]] if only_sig else df
    if view.empty:
        st.success("No significant trends at this level after FDR control. That is the honest result.")
    else:
        show_df(view.drop(columns=["level", "seasonality"]).round(4))
    ent = st.selectbox("Plot entity", list(df["entity"]))
    show_plot(px.line(monthly_prevalence(an.baskets[level], ent), x="month", y="prevalence", markers=True, title=ent))
    context_bm = an.baskets["family"]
    context = context_bm.receipts.assign(observed_families=context_bm.X.sum(1)).groupby("month")["observed_families"].mean().reset_index()
    context["month"] = context["month"].map(dict(enumerate(context_bm.month_labels)))
    with st.expander("Basket-size context"):
        show_plot(px.line(context, x="month", y="observed_families", markers=True, title="Mean observed families per receipt"))
        st.caption("Category prevalence can change when baskets become larger or smaller. The trend test conditions on consumer identity, but does not fully adjust for changing basket composition.")

with t_hier:
    st.write("Top-down testing: children are tested only under significant parents, using a conservative global Bonferroni threshold for descendants.")
    show_df(an.hier_trends[["entity", "tested", "prevalence", "slope_pp_per_month", "q", "q_hier", "significant_hier"]].round(4))

with t_pairs:
    pair_level = st.selectbox("Co-purchase hierarchy level", ["family", "brand", "function", "category"])
    source_key = str(id(an))
    pairs = get_level_pairs(pair_level, an, source_key)
    st.write("`naive_lift` pools all baskets; `adj_lift` divides by the count expected given each consumer's own habits and receipt sizes.")
    st.caption("Consumer bootstrap bounds describe pooled lift. Finite permutation resolution may prevent individual pairs from surviving correction. Showing no discoveries is a valid outcome.")
    p = lens.annotate_pairs(pairs, pl.hierarchy, pair_level).drop(columns=["_i", "_j"], errors="ignore").copy()
    if pair_level == "family":
        p["family_a"] = p["family_a"].map(lambda x: names.get(x, x)); p["family_b"] = p["family_b"].map(lambda x: names.get(x, x))
    q_max = st.slider("FDR q threshold", 0.001, 0.2, 0.05)
    p = p[p["q"] < q_max]
    if lens.active:
        adj_only = st.checkbox(f"Only pairs adjacent to the {lens.name} portfolio", value=False)
        if adj_only:
            p = p[p["portfolio_adjacent"] == True]  # noqa: E712
    show_df(p.round(4))
    fig = px.scatter(pairs, x="naive_lift", y="adj_lift", color=pairs["q"] < 0.05, hover_data=["family_a", "family_b", "count"],
                     title="Naive vs consumer-adjusted lift (adj_lift near 1 = explained by consumer identity)")
    show_plot(fig)

with t_brand:
    brands = sorted(pl.hierarchy["brand"].dropna().unique())
    b = st.selectbox("Brand", brands)
    cats = sorted(pl.hierarchy.loc[pl.hierarchy["brand"] == b, "category"].unique())
    c = st.selectbox("Category", cats)
    d = brand_share_decomposition(pl.lines, b, c)
    st.write("Brand prevalence change = **category growth** + **share-of-category change**. Without the split a brand gets credit for the whole category moving.")
    show_df(d.round(4))
