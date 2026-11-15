import pandas as pd
from needstate.opportunities import portfolio_opportunities
from needstate.ingestion.adapters import to_canonical
from needstate.workspace import config
from tests.test_workspace import ROW


def test_portfolio_forecast_is_temporal_and_conditional():
    rows=[]
    for buyer in range(25):
        for month in range(1,7):
            rows.append(dict(customer_id=str(buyer),transaction_id=f'{buyer}-{month}',timestamp=pd.Timestamp(2026,month,1),brand='A',owner='P&G',category='laundry'))
    data=pd.DataFrame(rows)
    result=portfolio_opportunities(data,data[['category','owner','brand']].drop_duplicates())[0]
    assert result['relevant'] and result['forecast']['rate']==100
    assert result['forecast']['validation_buyers']==25
    data.loc[data.timestamp.dt.month==6,'brand']=None
    result=portfolio_opportunities(data,data[['category','owner','brand']].drop_duplicates())[0]
    assert result['coverage']<100


def test_missing_receipt_metadata_recovered_only_when_unambiguous():
    frame=pd.DataFrame([ROW,ROW],columns=['Receipt ID','Consumer ID','Date','Product Name','Line Number','Quantity','Unit Price','Line Total'])
    frame.loc[1,'Date']=None
    frame.loc[1,'Consumer ID']=None
    result=to_canonical(frame,config().mapping)
    assert result.timestamp.notna().all()
    assert result.customer_id.nunique()==1
