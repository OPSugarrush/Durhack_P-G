@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
if not exist ".venv\Scripts\python.exe" (
  echo Create the Python environment using the instructions in README.md first.
  pause
  exit /b 1
)
set "PYTHONPATH=%CD%\src"
".venv\Scripts\python.exe" -m needstate.webapp --open
pause
