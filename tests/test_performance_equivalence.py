"""Optimisations must preserve classifications, ordering, and graph partitions."""
from unittest.mock import patch

import networkx as nx
import pandas as pd
from networkx.algorithms.community import greedy_modularity_communities

from needstate.business_outlook import _brand_histories
from needstate.need_state.decomposition import decompose_basket


def test_uniform_cliques_match_original_greedy_algorithm():
    for sizes in [(1,), (2,), (7,), (1, 2, 4), (3, 5, 2)]:
        profiles, graph = {}, nx.Graph()
        for category, size in enumerate(sizes):
            names = [f'{category}-{i}' for i in range(size)]
            graph.add_nodes_from(names)
            for name in names:
                profiles[name] = dict(function=str(category), category=str(category), department='all')
            for i, a in enumerate(names):
                for b in names[i+1:]:
                    graph.add_edge(a, b, weight=1.0)
        expected = list(greedy_modularity_communities(graph, weight='weight')) if graph.number_of_edges() else [{f} for f in profiles]
        expected = sorted((sorted(c) for c in expected), key=lambda c: (-len(c), c))
        with patch('needstate.need_state.decomposition.greedy_modularity_communities', side_effect=AssertionError('Uniform cliques should not need greedy optimisation')):
            actual = decompose_basket(list(profiles), pd.DataFrame(), profiles=profiles, replicated={})
        assert [p.families for p in actual] == expected
        assert all(not p.ambiguous for p in actual)


def test_weighted_mixture_still_uses_original_algorithm():
    profiles = {str(i): dict(function=str(i//3), category='one', department='all') for i in range(6)}
    with patch('needstate.need_state.decomposition.greedy_modularity_communities', wraps=greedy_modularity_communities) as original:
        decompose_basket(list(profiles), pd.DataFrame(), profiles=profiles, replicated={})
    original.assert_called_once()


def test_history_preserves_unknown_brands_and_duplicate_lines():
    rows = []
    for i, brand in enumerate(['A', 'A', 'B', 'B']):
        rows.append(dict(customer_id='one', transaction_id=str(i), timestamp=pd.Timestamp('2026-01-01')+pd.Timedelta(days=i), brand=brand, owner='shared', retailer_id='shop', recent=i>=2))
    frame = pd.DataFrame(rows)
    result = _brand_histories(pd.concat([frame, frame.iloc[[2]]]))[0]
    assert result['status'] == 'Possible switch'
    assert result['owner_movement'] == 'Same owner'
    assert len(result['timeline']) == 4
    frame.loc[3, 'brand'] = None
    assert _brand_histories(frame)[0]['status'] == 'Insufficient history'
