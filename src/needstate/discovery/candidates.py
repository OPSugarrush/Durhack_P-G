"""Exploratory communities supported by corrected co-purchase evidence."""
import hashlib
import networkx as nx
import pandas as pd

def discover_candidates(bm, pairs, hierarchy, needs_cfg, q_max=0.05):
    columns = ["candidate_id", "families", "functions", "mean_adj_lift", "taxonomy_coverage", "credibility_factors", "n_factors_agreeing"]
    graph = nx.Graph()
    for row in pairs[pairs["q"] < q_max].itertuples():
        if row.adj_lift > 1:
            graph.add_edge(row.family_a, row.family_b, weight=row.adj_lift - 1)
    if not graph.number_of_edges():
        return pd.DataFrame(columns=columns)
    h = hierarchy.set_index("family_id")
    rows = []
    for group in nx.community.greedy_modularity_communities(graph, weight="weight"):
        fs = sorted(group)
        funcs = sorted(set(h.loc[fs, "function"]) - {"unclassified"})
        covered = any(set(funcs) <= set(n["functions"]) for n in needs_cfg["need_states"])
        factors = {"adjusted_pair_evidence": True, "held_out_replication": False, "human_review": False}
        rows.append(dict(candidate_id="cand-" + hashlib.sha256("|".join(fs).encode()).hexdigest()[:10], families=fs,
                         functions=funcs, mean_adj_lift=sum(d["weight"] + 1 for _, _, d in graph.subgraph(fs).edges(data=True)) / graph.subgraph(fs).number_of_edges(),
                         taxonomy_coverage="covered" if covered else "candidate outside seed taxonomy",
                         credibility_factors=factors, n_factors_agreeing=sum(factors.values())))
    return pd.DataFrame(rows, columns=columns)
