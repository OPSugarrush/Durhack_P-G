import pandas as pd

from needstate.need_state.observations import replicated_pairs
from needstate.webapp import Store, demo
from needstate.workspace import config
from needstate.mission_review import review_rows, compare


def test_replicated_and_period_specific_pairs():
    rows = []
    for period in range(2):
        for buyer in range(6):
            for trip in range(16):
                pair = ("AB","CD")[trip%2] if period==0 else ("AB","CE")[trip%2]
                for product in pair:
                    rows.append(dict(transaction_id=f"{period}-{buyer}-{trip}", customer_id=buyer,
                                     retailer_id="store", family_id=product,
                                     timestamp=pd.Timestamp("2025-01-01")+pd.Timedelta(days=period*100+trip)))
    confirmed, variable = replicated_pairs(pd.DataFrame(rows))
    assert ("A","B") in confirmed and ("C","D") in variable
    assert ("A","C") not in confirmed


def test_reviewer_disagreements_are_detected():
    store = Store()
    store.run(None)
    rows = pd.DataFrame(review_rows(store.report, 3))
    assert compare(store.report,rows)==[]
    rows["group"]="one"
    results = compare(store.report,rows)
    assert any(r["label_disagreements"] for r in results)
