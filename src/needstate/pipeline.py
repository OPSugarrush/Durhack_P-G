"""Orchestrates Layers 1-3 plus receipt quality. Higher layers take a PipelineResult."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from needstate.config import Config, load_config
from needstate.ingestion.adapters import load_lines
from needstate.product_intel.entity_resolution import ResolutionResult, resolve_products
from needstate.product_intel.hierarchy import attach_hierarchy, build_hierarchy
from needstate.product_intel.portfolio import PortfolioLens
from needstate.validation.checks import receipt_quality, reconcile


@dataclass
class PipelineResult:
    config: Config
    lines: pd.DataFrame          # canonical + family_id + hierarchy columns
    resolution: ResolutionResult
    hierarchy: pd.DataFrame
    quality: pd.DataFrame        # per-receipt data_completeness
    audit: dict
    lens: PortfolioLens


def process_lines(lines: pd.DataFrame, config: Config) -> PipelineResult:
    p = config.params
    counts = lines["raw_product_text"].value_counts()
    if counts.empty:
        raise ValueError("No readable product descriptions remain in this source.")
    res = resolve_products(
        counts,
        config.abbreviations,
        min_prefix_len=p.get("min_prefix_len", 20),
        fuzzy_review_threshold=p.get("fuzzy_review_threshold", 0.90),
    )
    fam = lines.merge(
        res.variant_map[["raw_text", "family_id", "confidence"]].rename(columns={"confidence": "match_confidence"}),
        left_on="raw_product_text",
        right_on="raw_text",
        how="left",
    ).drop(columns="raw_text")
    hier = build_hierarchy(res.catalogue, config.hierarchy)
    full = attach_hierarchy(fam, hier)
    return PipelineResult(
        config=config,
        lines=full,
        resolution=res,
        hierarchy=hier,
        quality=receipt_quality(full),
        audit=reconcile(lines),
        lens=PortfolioLens.from_config(config.lens),
    )


def run(config_path: str = "configs/pipeline.yaml") -> PipelineResult:
    cfg = load_config(config_path)
    lines = load_lines(cfg.input_path, cfg.mapping)
    return process_lines(lines, cfg)
