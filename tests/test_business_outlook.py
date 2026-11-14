import pandas as pd
from needstate.business_outlook import business_outlook
from needstate.business_outlook import category_reach


def test_recent_reach_includes_buyers_without_earlier_history():
    data=fixture()
    new=data.iloc[[-1]].copy()
    new['customer_id']='New';new['transaction_id']='New-trip'
    result=category_reach(pd.concat([data,new,new]),'2026-02-20')
    assert result[0]['buyers']==2 and result[0]['total']==2
    assert result[0]['reach']==100


def fixture(unknown=False):
    rows=[]
    for i in range(6):
        rows.append(dict(customer_id='C',transaction_id=str(i),timestamp=pd.Timestamp('2026-01-01')+pd.Timedelta(days=i*20),category='laundry',brand='A' if i<3 else 'B',owner='Company',retailer_id='Shop'))
    if unknown: rows[-1]['brand']=None
    return pd.DataFrame(rows)


def test_internal_switch_does_not_become_owner_loss():
    result=business_outlook(fixture(),'2026-02-20',{})[0]
    h=result['histories'][0]
    assert h['status']=='Possible switch'
    assert h['owner_movement']=='Same owner'
    assert result['movements']['owner'][0]['earlier']==100
    assert result['movements']['owner'][0]['recent']==100
    assert result['status']=='Insufficient evidence'


def test_unknown_brands_prevent_switch_claim():
    result=business_outlook(fixture(True),'2026-02-20',{})[0]
    assert result['histories'][0]['status']=='Insufficient history'


def test_multiple_same_owner_brands_count_one_trip():
    data=fixture()
    extra=data.iloc[[0]].copy();extra['brand']='B'
    result=business_outlook(pd.concat([data,extra]),'2026-02-20',{})[0]
    assert result['movements']['owner'][0]['earlier']==100
