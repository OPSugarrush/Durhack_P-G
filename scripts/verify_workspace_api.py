"""Exercise upload, preview, safe append, conflicts and browser isolation on a running server."""
import argparse
import io
import time
import requests
import pandas as pd

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:8502')
args=parser.parse_args()
s=requests.Session();s.trust_env=False
base=args.url
assert s.get(base,timeout=10).status_code==200

def finish():
    for _ in range(180):
        response=s.get(base+'/api/state?job=1',timeout=10).json()
        job=response['job']
        if job['status']!='running': return job
        time.sleep(1)
    raise AssertionError('Import timed out')

rows=[]
for c in range(24):
    for k in range(10):
        rows.append({'Receipt ID':f'{c}-{k}','Consumer ID':f'c{c}','Date':str(pd.Timestamp('2026-01-01')+pd.Timedelta(days=k*18)),
                     'Product Name':'ARIEL NON BIO PODS' if k>=5 else 'BANANAS 5 PK','Quantity':1,'Unit Price':2,'Line Total':2,'Line Number':1})
csv=pd.DataFrame(rows).to_csv(index=False)
def upload(text):
    response=s.post(base+'/api/upload',files={'file':('test.csv',text,'text/csv')},timeout=30)
    assert response.status_code==200,response.text
    assert response.json()['sheets'][0]['ready']

upload(csv)
assert s.post(base+'/api/import',json={'sheet':'CSV','mode':'replace','synthetic':True},timeout=10).status_code==202
assert finish()['status']=='complete'
report=s.get(base+'/api/state',timeout=30).json()['report']
assert report['totals']['receipts']==240
assert report['totals']['comparable']==24
assert any(i['signal']=='supported' for i in report['insights'])
print('PASS upload -> preview -> analysis -> findings',flush=True)
upload(csv)
s.post(base+'/api/import',json={'sheet':'CSV','mode':'append','synthetic':True},timeout=10)
assert finish()['status']=='complete'
report=s.get(base+'/api/state',timeout=30).json()['report']
assert report['totals']['receipts']==240 and report['import_result']['skipped_receipts']==240
print('PASS duplicate append leaves receipt counts unchanged',flush=True)
upload(csv.replace('BANANAS 5 PK','BANANAS 6 PK',1))
s.post(base+'/api/import',json={'sheet':'CSV','mode':'append','synthetic':True},timeout=10)
assert finish()['status']=='error'
assert s.get(base+'/api/state',timeout=30).json()['report']['totals']['receipts']==240
print('PASS conflicting append preserves existing dataset',flush=True)
other=requests.Session();other.trust_env=False;other.get(base,timeout=10)
assert other.get(base+'/api/state',timeout=10).json()['report'] is None
assert s.get(base+'/api/export',timeout=10).status_code==200
assert s.post(base+'/api/demo',headers={'Origin':'https://unrelated.example'},timeout=10).status_code==403
print('PASS isolated workspaces, CSV export, origin protection',flush=True)
