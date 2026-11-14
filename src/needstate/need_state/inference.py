"""P1: multi-label need-state scoring PER PARTITION (baseline: transparent weak-supervision rules).

score(need, partition) = (1 - 0.5**n_support) * (0.5 + 0.5 * purity)
  n_support = products in the partition whose function serves the need
  purity    = n_support / partition size
Scores are independent per (need, partition); they are never normalised to sum to 1 and never
divided by the number of candidates (see strategy doc, "Confidence design"). This baseline is the
seed for a learned multi-label head (CatBoost/sklearn) validated on human-annotated holdouts.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from needstate.need_state.decomposition import Partition, decompose_basket


@dataclass
class BasketPrediction:
    basket_id: str
    mission_partitions: list[dict]
    candidate_needs: list[dict]
    evidence_concentration: float
    data_completeness: float
    model_confidence: float
    abstained: bool
    unexplained_products: list[str] = field(default_factory=list)


def score_partition(part: Partition, hierarchy_idx: pd.DataFrame, needs: list[dict]) -> list[dict]:
    out = []
    funcs = {f: hierarchy_idx.loc[f, "function"] for f in part.families}
    for n in needs:
        support = [f for f, fn in funcs.items() if fn in n["functions"]]
        if not support:
            continue
        purity = len(support) / len(part.families)
        score = (1 - 0.5 ** len(support)) * (0.5 + 0.5 * purity)
        out.append(
            {
                "need_state_id": n["id"],
                "label": n["label"],
                "partition_id": part.partition_id,
                "score": round(float(score), 4),
                "supporting_product_ids": support,
                "contradictory_evidence": [],
                "other_partition_products": [f for f in part.families if f not in support],
                "alternative_explanations": ["Routine replenishment", "Unrelated purchases", "Purchases for several people"],
            }
        )
    return out


def evidence_concentration(scores: list[float]) -> float:
    """Top-two margin of candidate scores in [0,1]; low = diffuse/hedged. Does NOT alter any score."""
    s = sorted(scores, reverse=True)
    if not s:
        return 0.0
    return float(s[0] - (s[1] if len(s) > 1 else 0.0))


def predict_basket(
    basket_id: str,
    families: list[str],
    hierarchy: pd.DataFrame,
    needs_cfg: dict,
    data_completeness: float = 1.0,
    match_confidence: dict[str, float] | None = None,
    assoc: pd.DataFrame | None = None,
) -> BasketPrediction:
    th = needs_cfg.get("thresholds", {})
    hidx = hierarchy.set_index("family_id")
    parts = decompose_basket(families, hierarchy, assoc=assoc, ambiguity_ratio=th.get("ambiguity_ratio", 0.8))
    cands: list[dict] = []
    for p in parts:
        cands += score_partition(p, hidx, needs_cfg["need_states"])
    cands.sort(key=lambda c: -c["score"])
    explained = {f for c in cands for f in c["supporting_product_ids"]}
    top = cands[0] if cands else None
    mc = match_confidence or {}
    model_conf = float(np.mean([mc.get(f, 1.0) for f in top["supporting_product_ids"]])) * top["score"] if top else 0.0
    abstained = (
        top is None
        or top["score"] < th.get("abstain_below_score", 0.35)
        or data_completeness < th.get("abstain_below_completeness", 0.6)
    )
    return BasketPrediction(
        basket_id=basket_id,
        mission_partitions=[{"partition_id": p.partition_id, "product_ids": p.families, "ambiguous_product_ids": p.ambiguous} for p in parts],
        candidate_needs=cands,
        evidence_concentration=evidence_concentration([c["score"] for c in cands]),
        data_completeness=float(data_completeness),
        model_confidence=round(model_conf, 4),
        abstained=bool(abstained),
        unexplained_products=sorted(set(families) - explained),
    )


def predict_all(lines: pd.DataFrame, hierarchy: pd.DataFrame, needs_cfg: dict, quality: pd.DataFrame, assoc: pd.DataFrame | None = None, limit: int | None = None, transaction_ids: set | None = None) -> pd.DataFrame:
    """Top-need summary per receipt (flat frame for dashboards and the missing-data harness)."""
    rows = []
    mconf = lines.drop_duplicates("family_id").set_index("family_id")["match_confidence"].to_dict() if "match_confidence" in lines else None
    for k, (tid, g) in enumerate(lines.dropna(subset=["family_id"]).groupby("transaction_id")):
        if transaction_ids is not None and tid not in transaction_ids:
            continue
        if limit and len(rows) >= limit:
            break
        pred = predict_basket(
            tid,
            list(g["family_id"].unique()),
            hierarchy,
            needs_cfg,
            data_completeness=float(quality["data_completeness"].get(tid, 1.0)),
            match_confidence=mconf,
            assoc=assoc,
        )
        top = pred.candidate_needs[0] if pred.candidate_needs else None
        rows.append(
            {
                "transaction_id": tid,
                "n_partitions": len(pred.mission_partitions),
                "n_candidates": len(pred.candidate_needs),
                "top_need": top["need_state_id"] if top else None,
                "top_score": top["score"] if top else 0.0,
                "needs": sorted({c["need_state_id"] for c in pred.candidate_needs if c["score"] >= needs_cfg.get("thresholds", {}).get("abstain_below_score", 0.35)}),
                "evidence_concentration": pred.evidence_concentration,
                "data_completeness": pred.data_completeness,
                "model_confidence": pred.model_confidence,
                "abstained": pred.abstained,
            }
        )
    return pd.DataFrame(rows)
