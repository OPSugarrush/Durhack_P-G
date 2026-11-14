"""Local-only web API with isolated browser workspaces and background import jobs."""
from __future__ import annotations
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
import io
import json
import logging
import math
from pathlib import Path
import secrets
import threading
import time

import numpy as np
import pandas as pd
from starlette.applications import Starlette
from starlette.responses import JSONResponse,FileResponse,Response
from starlette.routing import Route,Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from needstate.config import ROOT,load_config
from needstate.pipeline import process_lines
from needstate.workspace.imports import parse_source,preview,canonical,merge_lines,MAX_BYTES
from needstate.workspace.report import build_report

STATIC=ROOT/'web'
POOL=ThreadPoolExecutor(max_workers=2)
SESSIONS={}
LOCK=threading.RLock()

def clean(value):
    if isinstance(value,dict): return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [clean(v) for v in value]
    if isinstance(value,(np.integer,)): return int(value)
    if isinstance(value,(np.floating,float)): return float(value) if math.isfinite(value) else None
    if isinstance(value,np.bool_): return bool(value)
    if value is pd.NA or value is pd.NaT: return None
    if isinstance(value,pd.Timestamp): return value.isoformat()
    return value

def answer(value,status=200): return JSONResponse(clean(value),status_code=status)

def session(request):
    sid=request.cookies.get('needstate_workspace')
    with LOCK:
        if sid not in SESSIONS: raise ValueError('Your workspace expired. Refresh the page and import again.')
        SESSIONS[sid]['seen']=time.time()
        return SESSIONS[sid]

async def home(request):
    with LOCK:
        expired=[k for k,v in SESSIONS.items() if time.time()-v['seen']>7200 and not v.get('busy')]
        for k in expired: SESSIONS.pop(k)
        sid=request.cookies.get('needstate_workspace')
        if sid not in SESSIONS:
            if len(SESSIONS)>=16: return Response('Too many local workspaces are open. Close old sessions and restart the server.',status_code=503)
            sid=secrets.token_urlsafe(24)
            SESSIONS[sid]=dict(seen=time.time(),frames=None,lines=None,report=None,sources=[],job=None,busy=False)
    response=FileResponse(STATIC/'index.html')
    response.set_cookie('needstate_workspace',sid,httponly=True,samesite='strict')
    response.headers['Cache-Control']='no-store'
    return response

def same_origin(request):
    origin=request.headers.get('origin')
    return not origin or origin.rstrip('/') == str(request.base_url).rstrip('/')

async def state(request):
    s=session(request)
    if request.query_params.get('job'):
        return answer(dict(job=s['job']))
    return answer(dict(report=s['report'],job=s['job'],sources=s['sources']))

def start_job(s,work):
    with LOCK:
        if s['busy']: raise ValueError('An import is already running. Wait for it to finish.')
        s['busy']=True; s['job']=dict(status='running',stage='Checking receipt data',progress=10)
    def execute():
        try: work()
        except Exception as exc:
            logging.getLogger(__name__).exception('Workspace import failed')
            with LOCK: s['job']=dict(status='error',message=str(exc) if isinstance(exc,ValueError) else 'We could not process this file. Check its dates, columns and receipt IDs, then try again.')
        finally:
            with LOCK: s['busy']=False
    POOL.submit(execute)

def update(s,stage,progress):
    with LOCK: s['job']=dict(status='running',stage=stage,progress=progress)

def analyse(s,lines,sources,synthetic,skipped=0,duplicates=0):
    update(s,'Resolving products and purchase categories',35)
    cfg=load_config(ROOT/'configs/pipeline.yaml')
    pl=process_lines(lines,cfg)
    update(s,'Comparing customer histories',65)
    result=clean(build_report(pl,sources,synthetic))
    result['import_result']=dict(skipped_receipts=skipped,duplicate_rows=duplicates)
    with LOCK:
        s.update(lines=lines,report=result,sources=sources,frames=None)
        s['job']=dict(status='complete',progress=100,stage='Findings ready')

async def upload(request):
    if not same_origin(request): return answer({'error':'Import must originate from this workspace.'},403)
    s=session(request)
    if s['busy']: raise ValueError('Wait for the current import to finish.')
    async with request.form(max_files=1,max_fields=2,max_part_size=MAX_BYTES) as form:
        file=form.get('file')
        if not file or not hasattr(file,'read'): raise ValueError('Choose a receipt workbook first.')
        payload=await file.read(MAX_BYTES+1); name=Path(file.filename or 'receipts.xlsx').name
    try:
        frames=await asyncio.get_running_loop().run_in_executor(POOL,parse_source,payload,name)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('This file could not be read. Save it as a standard Excel workbook (.xlsx) or UTF-8 CSV, then try again.') from exc
    s['frames']=frames; s['filename']=name
    return answer(dict(filename=name,sheets=preview(frames)))

async def commit_import(request):
    if not same_origin(request): return answer({'error':'Import must originate from this workspace.'},403)
    s=session(request); body=await request.json()
    if s['frames'] is None: raise ValueError('Upload a file before starting the analysis.')
    sheet=body.get('sheet'); mode=body.get('mode','replace')
    if sheet not in s['frames']: raise ValueError('Choose a sheet from this workbook.')
    if mode not in ['replace','append']: raise ValueError('Choose a valid import mode.')
    frame=s['frames'][sheet].copy(); name=s['filename']; synthetic=bool(body.get('synthetic',False))
    if mode=='append' and s['report'] and s['report']['synthetic'] != synthetic:
        raise ValueError('Demo and real data cannot be combined. Start a separate dataset or match the synthetic-data setting.')
    def work():
        incoming,duplicates=canonical(frame)
        lines,skipped=merge_lines(s['lines'] if mode=='append' else None,incoming)
        source=dict(name=name,sheet=sheet,rows=len(incoming),receipts=incoming.transaction_id.nunique())
        sources=([*s['sources'],source] if mode=='append' else [source])
        analyse(s,lines,sources,synthetic,skipped,duplicates)
    start_job(s,work)
    return answer({'accepted':True},202)

async def demo(request):
    if not same_origin(request): return answer({'error':'Request must originate from this workspace.'},403)
    s=session(request)
    def work():
        path=load_config(ROOT/'configs/pipeline.yaml').input_path
        if not path.exists(): raise ValueError('The demo workbook is not bundled in Git. Upload your P&G-format workbook to get started.')
        frames=parse_source(path.read_bytes(),path.name)
        selected=next((name for name,df in frames.items() if set(['Receipt ID','Product Name','Date','Consumer ID'])<=set(df)),None)
        if selected is None: raise ValueError('The demo workbook does not contain the expected receipt columns.')
        lines,duplicates=canonical(frames[selected])
        analyse(s,lines,[dict(name='Durhack sample receipts',sheet=selected,rows=len(lines),receipts=lines.transaction_id.nunique())],True,duplicates=duplicates)
    start_job(s,work)
    return answer({'accepted':True},202)

async def export(request):
    s=session(request)
    if not s['report']: raise ValueError('Import receipts before downloading findings.')
    cols=['name','dimension','confidence','headline','conclusion','action','customers','buyers','earlier','recent','change','low','high','q']
    data=pd.DataFrame(s['report']['insights']).reindex(columns=cols).to_csv(index=False)
    return Response(data,media_type='text/csv',headers={'Content-Disposition':'attachment; filename="needstate-findings.csv"'})

async def template(request):
    from needstate.workspace.imports import FIELDS
    return Response(','.join(FIELDS)+'\n',media_type='text/csv',headers={'Content-Disposition':'attachment; filename="receipt-format.csv"'})

async def error(request,exc): return answer({'error':str(exc)},400)

app=Starlette(routes=[Route('/',home),Route('/api/state',state),Route('/api/upload',upload,methods=['POST']),
    Route('/api/import',commit_import,methods=['POST']),Route('/api/demo',demo,methods=['POST']),
    Route('/api/export',export),Route('/api/template',template),Mount('/assets',StaticFiles(directory=str(STATIC),check_dir=False))],exception_handlers={ValueError:error})
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','testserver'])

def main():
    import uvicorn
    parser=argparse.ArgumentParser(description='Start the NeedState local web workspace')
    parser.add_argument('--port',type=int,default=8502)
    args=parser.parse_args()
    uvicorn.run(app,host='127.0.0.1',port=args.port)

if __name__=='__main__': main()
