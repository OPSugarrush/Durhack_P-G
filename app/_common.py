"""Shared Streamlit helpers. Keep logic in src/needstate; pages stay thin."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:      # works even before `pip install -e .`
    sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import streamlit as st

from needstate.config import load_config
from needstate.product_intel.portfolio import PortfolioLens

CONFIG_PATH = str(ROOT / "configs/pipeline.yaml")


def page(title: str, icon: str = "🧭") -> None:
    st.set_page_config(page_title=f"NeedState Engine - {title}", page_icon=icon, layout="wide")
    st.sidebar.markdown("## NEEDSTATE ENGINE\nConsumer evidence lab")
    with st.sidebar.expander("Dataset and mapping"):
        st.file_uploader("Receipt workbook or CSV", type=["xlsx", "csv"], key="source_upload")
        st.file_uploader("Optional field mapping (YAML)", type=["yaml", "yml"], key="mapping_upload")
        st.checkbox("This dataset is synthetic", value=load_config(CONFIG_PATH).synthetic, key="synthetic_source")
        st.caption("The supplied workbook mapping is used unless you upload another mapping. Files stay in this local app process.")
    st.markdown("<style>.block-container{max-width:1450px;padding-top:2rem}h1{letter-spacing:-.035em}div[data-testid='stMetric']{background:white;padding:1rem;border-radius:12px;border:1px solid #e2e8f0}</style>", unsafe_allow_html=True)
    st.title(f"{icon} {title}")
    st.caption("Observed purchases → product hierarchy → testable patterns → research hypotheses")


def show_df(df: pd.DataFrame, **kw) -> None:
    try:
        st.dataframe(df, hide_index=True, width="stretch", **kw)
    except TypeError:                       # older Streamlit
        st.dataframe(df, hide_index=True, use_container_width=True, **kw)


def show_plot(fig) -> None:
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


@st.cache_resource(show_spinner="Testing receipt patterns against consumer habits. The first run may take a few minutes…")
def _cached_analysis(source_bytes, source_name, mapping_bytes, signature, synthetic):
    from needstate.service import analyse
    cfg = load_config(CONFIG_PATH)
    cfg.synthetic = synthetic
    if source_bytes is not None:
        import io
        import yaml
        from needstate.ingestion.adapters import to_canonical
        from needstate.pipeline import process_lines
        mapping = yaml.safe_load(mapping_bytes) if mapping_bytes else cfg.mapping
        raw = pd.read_csv(io.BytesIO(source_bytes)) if source_name.endswith(".csv") else pd.read_excel(io.BytesIO(source_bytes), sheet_name=mapping.get("source", {}).get("sheet", 0))
        return analyse(CONFIG_PATH, pipeline=process_lines(to_canonical(raw, mapping), cfg))
    if not cfg.input_path.exists():
        return None
    from needstate.pipeline import process_lines
    from needstate.ingestion.adapters import load_lines
    return analyse(CONFIG_PATH, pipeline=process_lines(load_lines(cfg.input_path, cfg.mapping), cfg))


def get_analysis():
    cfg = load_config(CONFIG_PATH)
    src = st.session_state.get("source_upload")
    mapping = st.session_state.get("mapping_upload")
    dependencies = [Path(CONFIG_PATH), *list((ROOT / "configs").rglob("*.yaml"))]
    if cfg.input_path.exists():
        dependencies.append(cfg.input_path)
    signature = tuple((str(p), p.stat().st_mtime_ns) for p in dependencies)
    return _cached_analysis(src.getvalue() if src else None, src.name if src else "", mapping.getvalue() if mapping else None, signature, st.session_state.get("synthetic_source", cfg.synthetic))


@st.cache_resource(show_spinner="Scoring every basket (about 20 s, once per session)...")
def get_predictions():
    from needstate.need_state.inference import predict_all

    an = get_analysis()
    pl = an.pipeline
    return predict_all(pl.lines, pl.hierarchy, pl.config.need_states, pl.quality, assoc=an.pairs[an.pairs["q"] < 0.05])


def require_analysis():
    try:
        an = get_analysis()
    except (ValueError, KeyError, OSError) as exc:
        st.error(f"Could not analyse this source: {exc}")
        st.stop()
    if an is None:
        cfg = load_config(CONFIG_PATH)
        st.error(f"Input file not found: `{cfg.input_path}`. Copy the workbook into `data/raw/` or edit `configs/pipeline.yaml`.")
        st.stop()
    return an


def synthetic_banner(an) -> None:
    st.info(" ".join(an.notes))


def lens_sidebar(an) -> PortfolioLens:
    """Portfolio lens is a configurable overlay: empty = general-market mode."""
    st.sidebar.header("Portfolio lens")
    cfg_lens = PortfolioLens.from_config(an.pipeline.config.lens)
    owners = sorted(an.pipeline.hierarchy["owner"].dropna().unique())
    mode = st.sidebar.radio("Mode", ["Configured lens", "General market", "Custom owners"], index=0 if cfg_lens.active else 1)
    if mode == "General market":
        return PortfolioLens()
    if mode == "Custom owners":
        chosen = st.sidebar.multiselect("Focal owners", owners, default=owners)
        return PortfolioLens("custom", chosen, [])
    return cfg_lens


def family_names(an) -> dict[str, str]:
    return an.pipeline.hierarchy.set_index("family_id")["family_name"].to_dict()


@st.cache_resource(show_spinner="Testing co-purchase at the selected hierarchy level…")
def get_level_pairs(level, _analysis, source_signature):
    from needstate.patterns.cooccurrence import null_model_pairs, bootstrap_pair_ci
    if level == "family":
        return _analysis.pairs
    bm = _analysis.baskets[level]
    params = _analysis.pipeline.config.params
    pairs = null_model_pairs(bm, n_perm=params.get("n_perm", 999), seed=params.get("seed", 42), min_count=params.get("min_pair_count", 8))
    return bootstrap_pair_ci(bm, pairs, n_boot=300, seed=params.get("seed", 42))
