"""Portfolio lens: a configurable overlay, never a hardcoded assumption.

Empty focal_owners AND focal_brands => general-market mode (exposure/adjacency are None).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class PortfolioLens:
    name: str = "general market"
    focal_owners: list[str] = field(default_factory=list)
    focal_brands: list[str] = field(default_factory=list)

    @property
    def active(self) -> bool:
        return bool(self.focal_owners or self.focal_brands)

    @classmethod
    def from_config(cls, cfg: dict | None) -> "PortfolioLens":
        cfg = cfg or {}
        return cls(cfg.get("name", "general market"), list(cfg.get("focal_owners") or []), list(cfg.get("focal_brands") or []))

    def in_portfolio(self, hierarchy: pd.DataFrame) -> pd.Series:
        """Boolean per family row."""
        m = pd.Series(False, index=hierarchy.index)
        if self.focal_owners:
            m |= hierarchy["owner"].isin(self.focal_owners)
        if self.focal_brands:
            m |= hierarchy["brand"].isin(self.focal_brands)
        return m

    def portfolio_functions(self, hierarchy: pd.DataFrame) -> set[str]:
        return set(hierarchy.loc[self.in_portfolio(hierarchy), "function"])

    def annotate_pairs(self, pairs: pd.DataFrame, hierarchy: pd.DataFrame, level: str = "family") -> pd.DataFrame:
        """Add portfolio_exposure (share of the pair's families in the portfolio) and adjacency flag.

        pairs must carry family_a / family_b (family-level entities).
        """
        out = pairs.copy()
        if not self.active:
            out["portfolio_exposure"] = None
            out["portfolio_adjacent"] = None
            return out
        if level != "family":
            from needstate.product_intel.hierarchy import entity_column
            col = entity_column(level)
            temp = hierarchy.assign(_in=self.in_portfolio(hierarchy))
            exp = temp.groupby(col)["_in"].mean()
            functions = temp.groupby(col)["function"].agg(set).to_dict()
            pf = self.portfolio_functions(hierarchy) - {"unclassified"}
            out["portfolio_exposure"] = [(exp.get(a, 0) + exp.get(b, 0)) / 2 for a, b in zip(out.family_a, out.family_b)]
            out["portfolio_adjacent"] = [bool((functions.get(a, set()) | functions.get(b, set())) & pf) and e < 1 for a, b, e in zip(out.family_a, out.family_b, out.portfolio_exposure)]
            return out
        h = hierarchy.set_index("family_id")
        inp = self.in_portfolio(hierarchy)
        inp.index = hierarchy["family_id"]
        pf = self.portfolio_functions(hierarchy)
        out["portfolio_exposure"] = [
            (float(inp.get(a, False)) + float(inp.get(b, False))) / 2 for a, b in zip(out["family_a"], out["family_b"])
        ]
        out["portfolio_adjacent"] = [
            bool((h.loc[a, "function"] in pf or h.loc[b, "function"] in pf)) and e < 1.0
            for a, b, e in zip(out["family_a"], out["family_b"], out["portfolio_exposure"])
        ]
        return out

    def annotate_entities(self, entities: pd.DataFrame, hierarchy: pd.DataFrame, level: str = "family") -> pd.DataFrame:
        """Entity-level exposure: share of the entity's constituent families that are in the portfolio."""
        from needstate.product_intel.hierarchy import entity_column

        out = entities.copy()
        if not self.active:
            out["portfolio_exposure"] = None
            return out
        col = entity_column(level)
        h = hierarchy.assign(_in=self.in_portfolio(hierarchy))
        exp = h.groupby(col)["_in"].mean()
        out["portfolio_exposure"] = out["entity"].map(exp)
        funcs = h.groupby(col)["function"].agg(set)
        pf = self.portfolio_functions(hierarchy) - {"unclassified"}
        out["portfolio_adjacent"] = out["entity"].map(lambda e: bool(funcs.get(e, set()) & pf)) & (out["portfolio_exposure"] < 1)
        return out
