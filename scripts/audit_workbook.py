from pathlib import Path
import json,pandas as pd
root=Path.cwd()
with pd.ExcelFile(root/'data/raw/DH_Synthtic_Receipt_Database.xlsx') as x:
    result={}
    for sheet in x.sheet_names:
        df=x.parse(sheet)
        result[sheet]={'rows':len(df),'columns':len(df.columns),'dtypes':{k:str(v) for k,v in df.dtypes.items()},'missing':df.isna().sum().to_dict(),'duplicate_rows':int(df.duplicated().sum())}
(root/'data/processed/workbook_audit.json').write_text(json.dumps(result,indent=2,default=int))
print('Audited every sheet:',list(result))
