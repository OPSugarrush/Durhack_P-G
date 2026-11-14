"""Fallback runner for environments without pytest (CI and dev use pytest)."""
import importlib, inspect, sys, traceback, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
fails = 0; n = 0
for f in sorted(pathlib.Path("tests").glob("test_*.py")):
    mod = importlib.import_module(f"tests.{f.stem}")
    for name, fn in inspect.getmembers(mod, inspect.isfunction):
        if name.startswith("test_") and not inspect.signature(fn).parameters:
            n += 1
            try: fn(); print("PASS", f.stem, name)
            except Exception: fails += 1; print("FAIL", f.stem, name); traceback.print_exc()
print(f"\n{n - fails}/{n} passed"); sys.exit(1 if fails else 0)
