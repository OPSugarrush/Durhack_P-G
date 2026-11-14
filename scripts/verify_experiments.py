from pathlib import Path
from needstate.service import analyse, export
from needstate.validation_harness import injection
from needstate.pipeline import run
from needstate.missing_data.evaluation import run_experiment
import json
r=run()
out=Path('data/processed'); out.mkdir(parents=True,exist_ok=True)
null=injection.false_alarm_rate(r.lines,n_seeds=10)
(out/'false_alarm_study.json').write_text(json.dumps(null,indent=2))
tr=injection.trend_recovery(r.lines,n_trials=12)
tr.to_csv(out/'trend_recovery.csv',index=False)
print('FALSE ALARMS',null,flush=True); print(tr.to_string(index=False),flush=True)
md=run_experiment(r,r.config,kinds=['drop_lines_mcar','blank_names','blank_prices','drop_customer_ids','drop_receipts'],levels=(.1,.3),sample_receipts=60,progress=lambda p:print('missingness',round(p,2),flush=True))
md.to_csv(out/'missing_data_experiment.csv',index=False)
print(md.to_string(index=False),flush=True)
