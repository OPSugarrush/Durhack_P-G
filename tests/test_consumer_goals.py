import pandas as pd
from needstate.consumer_goals import spending_profiles


def test_spending_uses_line_totals_once_and_exposes_missing_prices():
    lines=pd.DataFrame(dict(customer_id=['A']*4, transaction_id=['R1','R1','R2','R3'],
        timestamp=pd.to_datetime(['2026-01-01']*2+['2026-02-01','2026-02-02']),
        category=['food']*4,line_total=[4,6,None,-3],receipt_total=[10,10,None,None]))
    p=spending_profiles(lines)[0]
    assert p['total']==10 and p['priced']==2 and p['lines']==4
    assert p['months'][1]['priced']==0
    assert p['trips']==3


def test_unidentified_receipts_do_not_become_a_person():
    lines=pd.DataFrame(dict(customer_id=[None],transaction_id=['R'],
        timestamp=pd.to_datetime(['2026-01-01']),category=['food'],line_total=[2]))
    assert spending_profiles(lines)==[]
