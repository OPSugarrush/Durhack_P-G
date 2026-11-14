import pandas as pd
import pytest

from needstate.workspace.imports import canonical, merge_lines, preview, parse_source
from needstate.workspace.report import classify, build_report
from needstate.pipeline import process_lines
from needstate.config import load_config


def frame():
    return pd.DataFrame({'Receipt ID':['r1','r2'], 'Consumer ID':['c1','c1'],
        'Date':['2026-01-01','2026-02-01'], 'Product Name':['ARIEL NON BIO PODS','BANANAS 5 PK'],
        'Quantity':[1,1], 'Unit Price':[3.,2.], 'Line Total':[3.,2.], 'Line Number':[1,1]})

def test_append_skips_identical_receipts_and_stops_conflicts():
    original,_=canonical(frame())
    combined,skipped=merge_lines(original,original.copy())
    assert len(combined)==2 and skipped==2
    altered=original.copy();altered.loc[0,'unit_price']=10.
    with pytest.raises(ValueError,match='different contents'):
        merge_lines(original,altered)
    assert original.loc[0,'unit_price']==3.

def test_append_adds_real_new_receipts():
    a,_=canonical(frame())
    new=frame();new['Receipt ID']=['r3','r4']
    b,_=canonical(new)
    result,skipped=merge_lines(a,b)
    assert len(result)==4 and skipped==0

def test_preview_and_bad_columns():
    f=frame().drop(columns='Consumer ID')
    assert preview({'sheet':f})[0]['missing']==['Consumer ID']
    with pytest.raises(ValueError,match='Consumer ID'):canonical(f)

def test_csv_support_and_blank_customer():
    f=frame();f.loc[0,'Consumer ID']=None
    frames=parse_source(f.to_csv(index=False).encode(),'receipts.csv')
    lines,_=canonical(frames['CSV'])
    assert pd.isna(lines.loc[0,'customer_id'])

def test_different_contents_with_same_line_number_are_not_deduplicated():
    f=frame();f['Receipt ID']='same';f['Date']='2026-01-01'
    with pytest.raises(ValueError,match='duplicate line numbers'):canonical(f)

def test_nuanced_individual_behaviour():
    assert classify(0,2,5,5)=='Newly observed'
    assert classify(3,0,5,5)=='No longer observed'
    assert classify(1,4,5,5)=='Buying more often'
    assert classify(4,1,5,5)=='Buying less often'
    assert classify(3,3,5,5)=='Established routine'
    assert classify(0,2,2,5)=='Not enough history'

def test_report_supports_population_shift_and_keeps_receipt_provenance():
    rows=[]
    for c in range(24):
        for k in range(10):
            base={'Receipt ID':f'{c}-{k}','Consumer ID':str(c),'Date':pd.Timestamp('2026-01-01')+pd.Timedelta(days=18*k),'Quantity':1,'Unit Price':2.,'Line Total':2.}
            rows.append({**base,'Product Name':'BANANAS 5 PK','Line Number':1})
            if k>=5:rows.append({**base,'Product Name':'ARIEL NON BIO PODS','Line Number':2})
    lines,_=canonical(pd.DataFrame(rows))
    report=build_report(process_lines(lines,load_config()),[],True)
    laundry=next(i for i in report['insights'] if i['id']=='category:laundry')
    assert laundry['signal']=='supported'
    assert laundry['states']['Newly observed']==24
    assert len(report['receipts']['0'])==10
    assert report['totals']['comparable']==24
    assert report['customers'][0]['score']==100

def test_no_customer_ids_returns_coverage_without_inventing_population():
    f=frame();f['Consumer ID']=None
    lines,_=canonical(f)
    report=build_report(process_lines(lines,load_config()),[],False)
    assert report['customers']==[] and report['insights']==[]
    assert report['totals']['unknown_customer_receipts']==2
