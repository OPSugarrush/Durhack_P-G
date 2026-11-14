"""One call that runs the whole analytical stack; used by the CLI and the Streamlit app."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from needstate.baskets.construction import BasketMatrix, build_basket_matrix
from needstate.discovery.candidates import discover_candidates
from needstate.patterns.cooccurrence import null_model_pairs, bootstrap_pair_ci
from needstate.patterns.routines import concentration, repeat_rates
from needstate.patterns.trends import hierarchical_scan, trend_scan
from needstate.pipeline import PipelineResult, run


@dataclass
class Analysis:
    pipeline: PipelineResult
    baskets: dict[str, BasketMatrix]
    pairs: pd.DataFrame
    trends: dict[str, pd.DataFrame]
    hier_trends: pd.DataFrame
    routines: pd.DataFrame
    routines_summary: dict
    repeat: pd.DataFrame
    candidates: pd.DataFrame
    notes: list[str] = field(default_factory=list)


def analyse(config_path: str = "configs/pipeline.yaml", pipeline: PipelineResult | None = None) -> Analysis:
    pl = pipeline if pipeline is not None else run(config_path)
    p = pl.config.params
    alpha = p.get("alpha", 0.05)
    baskets = {lv: build_basket_matrix(pl.lines, lv) for lv in ["family", "brand", "function", "category"]}
    bm = baskets["family"]
    pairs = null_model_pairs(bm, n_perm=p.get("n_perm", 999), seed=p.get("seed", 42), min_count=p.get("min_pair_count", 8))
    pairs = bootstrap_pair_ci(bm, pairs, n_boot=300, seed=p.get("seed", 42))
    pairs = pl.lens.annotate_pairs(pairs, pl.hierarchy)
    trends = {
        lv: trend_scan(b, n_perm=p.get("n_perm_trend", 0), alpha=alpha, min_support=20, min_cycles=p.get("min_cycles_for_seasonality", 2), seed=p.get("seed", 0))
        for lv, b in baskets.items()
    }
    fam_to_cat = pl.hierarchy.set_index("family_id")["category"].to_dict()
    hier = hierarchical_scan({"category": trends["category"], "family": trends["family"]}, {"family": fam_to_cat}, ["category", "family"], alpha=alpha)
    rdf, rsum = concentration(bm)
    cands = discover_candidates(bm, pairs, pl.hierarchy, pl.config.need_states, q_max=alpha)
    notes = [
        ("Dataset is synthetic: discoveries may reflect generator rules, not real consumers." if pl.config.synthetic else "Dataset provenance is user supplied; representativeness has not been validated."),
        "Promotion status is unknown where labels are missing. Retailer and promotion effects may be confounded; no causal promotion effect is estimated.",
        f"Observed span is {len(bm.month_labels)} months. Changes are descriptive; seasonal and emerging effects are not separated by this baseline.",
    ]
    for lv in trends:
        trends[lv] = pl.lens.annotate_entities(trends[lv], pl.hierarchy, lv)
    notes.append("Pair p-values use finite fixed-margin randomisation; the Monte Carlo resolution can limit FDR discoveries. Bootstrap intervals describe pooled lift, not adjusted lift.")
    return Analysis(pl, baskets, pairs, trends, hier, rdf, rsum, repeat_rates(bm), cands, notes)


def export(an: Analysis, out_dir: str | Path = "data/processed") -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    tables = {
        "catalogue.csv": an.pipeline.resolution.catalogue.assign(variants=lambda d: d["variants"].map("; ".join)),
        "hierarchy.csv": an.pipeline.hierarchy,
        "entity_review_pairs.csv": an.pipeline.resolution.review_pairs,
        "pairs_within_consumer_null.csv": an.pairs.drop(columns=["_i", "_j"], errors="ignore"),
        "trends_family.csv": an.trends["family"],
        "trends_category.csv": an.trends["category"],
        "trends_brand.csv": an.trends["brand"],
        "trends_hierarchical.csv": an.hier_trends,
        "consumer_routines.csv": an.routines,
        "candidates.csv": an.candidates.assign(families=lambda d: d["families"].map("; ".join)) if len(an.candidates) else an.candidates,
    }
    for name, df in tables.items():
        p = out / name
        df.to_csv(p, index=False)
        written.append(p)
    return written
