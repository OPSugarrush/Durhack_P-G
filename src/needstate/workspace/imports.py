"""Workbook preview and explicit, conflict-safe multi-file import."""
import io
import zipfile
import pandas as pd
from needstate.ingestion.adapters import to_canonical

MAX_BYTES=30*1024*1024
MAX_ROWS=150_000
FIELDS={'Receipt ID':'transaction_id','Consumer ID':'customer_id','Store Name':'retailer_id',
        'Store Address':'store_id','Date':'date','Time':'time','Product Name':'raw_product_text',
        'Quantity':'quantity','Unit Price':'unit_price','Line Total':'line_total','Total Spend':'receipt_total',
        'Promotion':'promotion_label','Line Number':'line_number','Image Filename':'image_ref'}
REQUIRED=['Receipt ID','Consumer ID','Date','Product Name']

def parse_source(payload, name):
    if len(payload)>MAX_BYTES: raise ValueError('This file is larger than 30 MB. Split it into smaller workbooks.')
    if name.lower().endswith('.xlsx'):
        with zipfile.ZipFile(io.BytesIO(payload)) as z:
            if sum(i.file_size for i in z.infolist())>250*1024*1024:
                raise ValueError('This workbook expands beyond the 250 MB import limit.')
        workbook=pd.ExcelFile(io.BytesIO(payload))
        frames={sheet:pd.read_excel(workbook,sheet_name=sheet,nrows=MAX_ROWS+1) for sheet in workbook.sheet_names[:20]}
        workbook.close()
    elif name.lower().endswith('.csv'):
        frames={'CSV':pd.read_csv(io.BytesIO(payload),nrows=MAX_ROWS+1)}
    else: raise ValueError('Choose an .xlsx workbook or .csv file.')
    for frame in frames.values():
        frame.columns=frame.columns.astype(str).str.strip()
        if len(frame)>MAX_ROWS: raise ValueError('A sheet exceeds 150,000 rows. Split it into smaller files.')
        if frame.columns.duplicated().any(): raise ValueError('Two columns have the same name. Give each column a unique header.')
    return frames

def preview(frames):
    output=[]
    for sheet,df in frames.items():
        missing=[c for c in REQUIRED if c not in df]
        output.append(dict(name=sheet,rows=len(df),columns=list(df.columns),missing=missing,ready=not missing and len(df)>0,
                           sample=df.head(4).astype('string').fillna('').to_dict('records')))
    return output

def canonical(frame):
    missing=[c for c in REQUIRED if c not in frame]
    if missing: raise ValueError('Add these required columns: '+', '.join(missing))
    if frame.empty: raise ValueError('This sheet has no receipt rows.')
    df=frame.copy()
    for col in ['Receipt ID','Consumer ID']:
        df[col]=df[col].astype('string').str.strip().replace('',pd.NA)
    if df['Receipt ID'].isna().any(): raise ValueError('Some rows have no Receipt ID. Fill those IDs before importing.')
    if df['Product Name'].isna().all(): raise ValueError('No readable product names were found.')
    # Identical exported rows are safe to deduplicate; conflicting line numbers are not.
    duplicates=int(df.duplicated().sum()); df=df.drop_duplicates()
    result=to_canonical(df,{'fields':{v:k for k,v in FIELDS.items() if k in df}})
    if result.duplicated(['transaction_id','line_number']).any():
        raise ValueError('A receipt has duplicate line numbers with different contents. Correct those lines before importing.')
    return result,duplicates

def merge_lines(existing,incoming):
    if existing is None: return incoming.copy(),0
    overlap=set(existing.transaction_id)&set(incoming.transaction_id)
    # Compare every supplied canonical value, order-independent, preserving missingness.
    def signature(g):
        return sorted(tuple(str(v) if pd.notna(v) else '' for v in row) for row in g.sort_index(axis=1).itertuples(index=False,name=None))
    for tid in overlap:
        if signature(existing[existing.transaction_id==tid]) != signature(incoming[incoming.transaction_id==tid]):
            raise ValueError(f'Receipt {tid} already exists with different contents. Choose a separate dataset or correct the conflicting receipt; existing data was not changed.')
    fresh=incoming[~incoming.transaction_id.isin(overlap)]
    combined=pd.concat([existing,fresh],ignore_index=True)
    if len(combined)>MAX_ROWS: raise ValueError('The combined dataset exceeds 150,000 rows. Start a separate dataset.')
    return combined,len(overlap)
