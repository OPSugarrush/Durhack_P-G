"""P2: shopping-mission decomposition. Runs BEFORE need-state scoring (see ADR-003).

Basket -> weighted product graph -> community detection -> sub-missions. Products whose pull toward
another community is comparable to their pull toward their own are flagged ambiguous, not forced.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np
import pandas as pd
from networkx.algorithms.community import greedy_modularity_communities


@dataclass
class Partition:
    partition_id: str
    families: list[str]
    ambiguous: list[str]


def functional_similarity(a: pd.Series, b: pd.Series) -> float:
    """Hierarchy-based similarity in [0, 1]: same function > same category > same department."""
    if a["function"] == b["function"] and a["function"] != "unclassified":
        return 1.0
    if a["category"] == b["category"] and a["category"] != "unclassified":
        return 0.6
    if a["department"] == b["department"] and a["department"] != "unclassified":
        return 0.15
    return 0.0


def decompose_basket(
    families: list[str],
    hierarchy: pd.DataFrame,
    assoc: pd.DataFrame | None = None,
    assoc_weight: float = 0.25,
    ambiguity_ratio: float = 0.8,
    profiles: dict | None = None,
    replicated: dict | None = None,
) -> list[Partition]:
    """assoc: optional pair table with family_a, family_b, adj_lift (consumer-adjusted) to blend in."""
    fams = list(dict.fromkeys(families))
    if not fams:
        return []
    h = profiles if profiles is not None else hierarchy.set_index("family_id").to_dict("index")
    lift = {}
    if assoc is not None and len(assoc):
        for a, b, v in zip(assoc["family_a"], assoc["family_b"], assoc["adj_lift"]):
            lift[(a, b)] = lift[(b, a)] = float(np.clip((v - 1.0) / 1.0, 0.0, 1.0)) if pd.notna(v) else 0.0
    G = nx.Graph()
    G.add_nodes_from(fams)
    for i, a in enumerate(fams):
        for b in fams[i + 1 :]:
            w = (1 - assoc_weight) * functional_similarity(h[a], h[b]) + assoc_weight * lift.get((a, b), 0.0)
            if replicated is not None:
                similarity = functional_similarity(h[a], h[b])
                observed = replicated.get(tuple(sorted((a,b))), 1.0)
                w = (similarity if similarity >= .6 or observed > 1 else 0) + min(2, observed - 1)
            if w > 0:
                G.add_edge(a, b, weight=w)
    if not G.number_of_edges():
        comms = [{f} for f in fams]
    else:
        components = list(nx.connected_components(G))
        # A disconnected union of constant-weight cliques has exactly these
        # communities under greedy modularity: every within-clique merge has
        # positive gain, and every cross-component merge has negative gain.
        # Keep the original algorithm for all other graphs (including weighted
        # category/function mixtures and evidence-linked components).
        uniform_cliques = True
        for component in components:
            weights = [weight for _, _, weight in G.edges(component, data='weight')]
            if len(weights) != len(component)*(len(component)-1)//2 or len(set(weights)) > 1:
                uniform_cliques = False
                break
        comms = components if uniform_cliques else list(greedy_modularity_communities(G, weight="weight"))
    comms = sorted((sorted(c) for c in comms), key=lambda c: (-len(c), c))
    owner = {f: k for k, c in enumerate(comms) for f in c}
    parts = []
    for k, c in enumerate(comms):
        amb = []
        for f in c:
            own = sum(G[f][o]["weight"] for o in c if o != f and G.has_edge(f, o))
            for k2, c2 in enumerate(comms):
                if k2 == k:
                    continue
                other = sum(G[f][o]["weight"] for o in c2 if G.has_edge(f, o))
                if other > 0 and (own == 0 or other >= ambiguity_ratio * own):
                    amb.append(f)
                    break
        parts.append(Partition(f"P{k + 1}", c, amb))
    return parts
