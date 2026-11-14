import pandas as pd
from needstate.customer_insights import analyse_customers

def test_repeated_customer_change_rolls_up_to_population():
    rows=[]
    for c in range(24):
        for k in range(10):
            base=dict(transaction_id=f'{c}-{k}',customer_id=str(c),timestamp=pd.Timestamp('2026-01-01')+pd.Timedelta(days=k*18))
            rows.append(dict(**base,category='food'))
            if k>=5: rows.append(dict(**base,category='laundry'))
    lines=pd.DataFrame(rows)
    quality=pd.DataFrame({'data_completeness':1.},index=lines.transaction_id.unique())
    customers,details,summary,*_=analyse_customers(lines,quality)
    assert customers.Evidence.eq(100).all()
    assert details[details.Category=='laundry'].Status.eq('Increasing').all()
    assert summary.set_index('Category').loc['laundry','Decision']=='Supported directional change'
    assert summary.set_index('Category').loc['food','Decision'].startswith('Monitor')

def test_thin_history_does_not_generate_population_claim():
    lines=pd.DataFrame({'transaction_id':['a','b'],'customer_id':['c','c'],'timestamp':pd.to_datetime(['2026-01-01','2026-04-01']),'category':['food','laundry']})
    q=pd.DataFrame({'data_completeness':[1.,1.]},index=['a','b'])
    customers,d,s,*_=analyse_customers(lines,q)
    assert s.empty
    assert d.Status.eq('Insufficient history').all()
    assert customers.Evidence.iloc[0]==20
