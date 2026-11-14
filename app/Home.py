import streamlit as st

from _common import lens_sidebar, page, require_analysis, show_df, synthetic_banner

page("NeedState Engine", "🧭")
an = require_analysis()
synthetic_banner(an)
lens = lens_sidebar(an)
pl = an.pipeline
a = pl.audit

c = st.columns(5)
c[0].metric("Line items", f"{a['n_lines']:,}")
c[1].metric("Receipts", f"{a['n_receipts']:,}")
c[2].metric("Consumers", f"{a['n_consumers']:,}")
c[3].metric("Raw product strings", f"{pl.resolution.variant_map.shape[0]:,}")
c[4].metric("Resolved families", f"{len(pl.resolution.catalogue):,}")

st.subheader("What this engine reports on this file")
fam = an.trends["family"]
st.markdown(
    f"""
1. **Product trends:** {int(fam['significant'].sum())} of {len(fam)} families significant after FDR
   ({int((fam['p_perm'] < .05).sum())} nominal p<0.05; about {0.05 * len(fam):.0f} expected by chance). Seasonality: *{fam['seasonality'].iloc[0]}*.
2. **Consumer routines dominate:** consumers are **{an.routines_summary['concentration_ratio']:.1f}x** more concentrated than the pooled data.
   Basket-level lift is therefore tested against a within-consumer null.
3. **Cross-purchase after consumer adjustment:** {int((an.pairs['q'] < .05).sum())} of {len(an.pairs):,} pairs survive FDR.
4. **Portfolio lens:** {'`' + lens.name + '` active' if lens.active else 'general-market mode'}.
"""
)
st.subheader("Where to go next")
st.markdown("Use the pages on the left: **Data Audit → Pattern Engine → Basket Explorer → Consumer Routines → Discovery & Review → Validation → Missing Data.**")
st.subheader("Download the evidence")
st.download_button("Family trend results", fam.to_csv(index=False), "needstate_family_trends.csv", "text/csv")
st.download_button("Consumer-adjusted co-purchase", an.pairs.drop(columns=["_i", "_j"]).to_csv(index=False), "needstate_adjusted_pairs.csv", "text/csv")
with st.expander("Caveats stated up front"):
    for n in an.notes:
        st.write("- " + n)
