from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def mission_graph(partitions: list[dict], names: dict[str, str], hierarchy: pd.DataFrame, assoc_weight_fn) -> go.Figure:
    """Basket product graph coloured by detected mission; ambiguous products get a diamond marker."""
    from needstate.need_state.decomposition import functional_similarity

    h = hierarchy.set_index("family_id")
    G = nx.Graph()
    part_of, amb = {}, set()
    for p in partitions:
        for f in p["product_ids"]:
            G.add_node(f)
            part_of[f] = p["partition_id"]
        amb |= set(p["ambiguous_product_ids"])
    fams = list(G.nodes)
    for i, a in enumerate(fams):
        for b in fams[i + 1 :]:
            w = functional_similarity(h.loc[a], h.loc[b])
            if w > 0:
                G.add_edge(a, b, weight=w)
    pos = nx.spring_layout(G, seed=3, weight="weight") if len(G) > 1 else {f: (0, 0) for f in G}
    ex, ey = [], []
    for a, b in G.edges:
        ex += [pos[a][0], pos[b][0], None]
        ey += [pos[a][1], pos[b][1], None]
    fig = go.Figure(go.Scatter(x=ex, y=ey, mode="lines", line=dict(width=1, color="#bbb"), hoverinfo="none", showlegend=False))
    palette = px.colors.qualitative.Set2
    for k, pid in enumerate(sorted(set(part_of.values()))):
        members = [f for f in fams if part_of[f] == pid]
        fig.add_trace(go.Scatter(
            x=[pos[f][0] for f in members], y=[pos[f][1] for f in members], mode="markers+text", name=f"Mission {pid}",
            text=[names.get(f, f)[:22] for f in members], textposition="top center",
            marker=dict(size=[22 if f in amb else 16 for f in members], color=palette[k % len(palette)],
                        symbol=["diamond" if f in amb else "circle" for f in members], line=dict(width=1, color="#333")),
        ))
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def monthly_prevalence(bm, entity: str) -> pd.DataFrame:
    i = bm.entities.index(entity)
    rows = []
    for m, lab in enumerate(bm.month_labels):
        sel = bm.month_idx == m
        rows.append({"month": lab, "prevalence": float(bm.X[sel, i].mean()), "receipts": int(sel.sum())})
    return pd.DataFrame(rows)
