import plotly.express as px
import streamlit as st
import pandas as pd
from pathlib import Path

from _common import page, require_analysis, show_df, show_plot, synthetic_banner
from needstate.validation_harness import injection as inj

page("Validation by Injection (no ground truth needed)", "✅")
an = require_analysis()
synthetic_banner(an)
lines = an.pipeline.lines

st.markdown("""
We cannot validate against true consumer motivation, so we **inject** known trends and bundles into the real data at several strengths and report
what the engine recovers and how often it raises false alarms. Four-part honest demo on this file:
1. measured organic trend flags and shuffled-null false alarms; 2. injection recovery by strength;
3. consumer-level routine structure; 4. cross-purchase patterns after consumer adjustment.
""")
st.caption("The data is synthetic: if discoveries match the generator's rules, that proves less than it seems.")

st.subheader("1. False alarms")
if st.button("Run false-alarm check"):
    r = inj.false_alarm_rate(lines, n_seeds=10)
    st.json(r)

st.subheader("2. Trend recovery by strength")
saved = Path("data/processed/trend_recovery.csv")
if saved.exists():
    st.caption("Last locally saved study. Recovery is against injected signals, not consumer motivation.")
    show_df(pd.read_csv(saved))
trials = st.slider("Trials per strength", 4, 40, 12)
if st.button("Run trend-recovery study"):
    df = inj.trend_recovery(lines, n_trials=trials)
    show_df(df)
    show_plot(px.line(df, x="added_prevalence_pp", y="recovery_rate", markers=True, range_y=[0, 1],
                      title="Share of injected upward ramps recovered (FDR 5%)"))

st.subheader("Bundle recovery")
if st.button("Run bundle-recovery study"):
    fams = lines["family_id"].value_counts().index
    pairs = [(fams[i], fams[i + 10]) for i in (5, 15, 25, 35)]
    show_df(inj.bundle_recovery(lines, pairs))
