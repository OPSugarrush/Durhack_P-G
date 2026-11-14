"""Hierarchy: variant -> family -> brand (nullable) -> function -> category -> department.

Brand may be empty today and filled later with no engine change: every consumer of the
hierarchy treats brand/owner as nullable.
"""
from __future__ import annotations

import re

import pandas as pd

from needstate.product_intel.entity_resolution import fold

LEVEL_COLUMN = {
    "variant": "raw_product_text",
    "family": "family_id",
    "brand": "brand",
    "function": "function",
    "category": "category",
    "department": "department",
}


def build_hierarchy(catalogue: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    brands = sorted((fold(b) for b in cfg.get("brands", [])), key=len, reverse=True)
    owner_of = {fold(b): owner for owner, bl in (cfg.get("owners") or {}).items() for b in bl}
    rules = [(re.compile(r["pattern"]), r) for r in cfg.get("rules", [])]
    default = cfg.get("default", {})
    rows = []
    for _, r in catalogue.iterrows():
        key = r["family_key"]
        brand = next((b for b in brands if key == b or key.startswith(b + " ")), None)
        match = next((rule for rx, rule in rules if rx.search(key)), default)
        rows.append(
            {
                "family_id": r["family_id"],
                "family_name": r["family_name"],
                "brand": brand,
                "owner": owner_of.get(brand) if brand else None,
                "function": match.get("function", "unclassified"),
                "category": match.get("category", "unclassified"),
                "department": match.get("department", "unclassified"),
            }
        )
    return pd.DataFrame(rows)


def entity_column(level: str) -> str:
    if level not in LEVEL_COLUMN:
        raise ValueError(f"Unknown level {level!r}; choose from {list(LEVEL_COLUMN)}")
    return LEVEL_COLUMN[level]


def attach_hierarchy(lines: pd.DataFrame, hierarchy: pd.DataFrame) -> pd.DataFrame:
    cols = ["family_id", "brand", "owner", "function", "category", "department"]
    return lines.merge(hierarchy[cols], on="family_id", how="left")
