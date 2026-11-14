import pandas as pd
from needstate.baskets.construction import build_basket_matrix
from needstate.patterns.transitions import entry_exit
from tests.helpers import mini_lines


def test_adjacent_entries_and_exits_are_observed_events():
    d = mini_lines().iloc[:3].copy()
    d['customer_id'] = 'c'
    d['transaction_id'] = ['a', 'b', 'c']
    d['family_id'] = ['x', 'y', 'x']
    d['timestamp'] = pd.date_range('2026-01-01', periods=3)
    result = entry_exit(build_basket_matrix(d)).set_index('entity')
    assert result.loc['x', 'observed_entries'] == 1
    assert result.loc['x', 'observed_exits'] == 1
    assert result.loc['y', 'observed_entries'] == 1
    assert result.loc['y', 'observed_exits'] == 1
