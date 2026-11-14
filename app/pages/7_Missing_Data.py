from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from _common import page, require_analysis, show_df, show_plot, synthetic_banner
from needstate.missing_data.evaluation import run_experiment
from needstate.missing_data.simulation import MECHANISM

page("Missing-Data Reliability", "🕳️")
an = require_analysis()
synthetic_banner(an)
SAVED = Path("data/processed/missing_data_experiment.csv")

kinds = st.multiselect("Corruption types", list(MECHANISM), default=["drop_lines_mcar", "drop_lines_mnar_price", "drop_receipts", "ocr_noise"])
levels = st.multiselect("Levels", [0.05, 0.10, 0.20, 0.30], default=[0.10, 0.30])
if st.button("Run experiment") and kinds and levels:
    bar = st.progress(0.0)
    df = run_experiment(an.pipeline, an.pipeline.config, kinds=kinds, levels=tuple(levels), progress=bar.progress)
    SAVED.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAVED, index=False)
elif SAVED.exists():
    df = pd.read_csv(SAVED)
    st.caption(f"Showing saved results from `{SAVED}`. Run `python -m needstate missing-data` to refresh.")
else:
    st.info("Pick corruption types and press Run.")
    st.stop()

metric = st.selectbox("Metric", ["need_top1_agreement", "pair_top30_jaccard", "match_completeness", "match_purity", "abstention_rate",
                                 "mean_model_confidence_shift", "receipts_remaining_share", "trend_flags_after_corruption"])
show_plot(px.line(df, x="level", y=metric, color="kind", line_dash="mechanism", markers=True))
st.caption("Whole missing receipts are reported as coverage loss (`receipts_remaining_share`), never reconstructed.")
show_df(df.round(3))
st.caption("Agreement and product-match metrics compare with the clean engine baseline, not verified consumer intentions or manually labelled product truth. Trend flags after corruption are not automatically false alarms.")
