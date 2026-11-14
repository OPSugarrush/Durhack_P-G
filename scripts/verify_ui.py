"""Exercise actual Streamlit page execution. Uses short randomisation for UI smoke only."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'app')]
from needstate.pipeline import run
from needstate.service import analyse
from streamlit.testing.v1 import AppTest
import _common

print("Loading UI fixture", flush=True)
pipeline = run()
pipeline.config.params['n_perm'] = 9
print("Analysing UI fixture", flush=True)
analysis = analyse(pipeline=pipeline)
print("Fixture ready", flush=True)
_common.get_analysis = lambda: analysis
failures = []
for path in [ROOT / 'app/Home.py', *sorted((ROOT / 'app/pages').glob('*.py'))]:
    app = AppTest.from_file(str(path)).run(timeout=90)
    errors = [str(e.value) for e in app.exception]
    print(path.name, errors or 'PASS', flush=True)
    failures.extend(errors)
    if path.name == '6_Validation.py':
        app.button[0].click().run(timeout=90)
        failures.extend(str(e.value) for e in app.exception)
        print('False-alarm button', 'PASS' if not app.exception else 'FAIL', flush=True)
if failures:
    raise SystemExit('\n'.join(failures))

