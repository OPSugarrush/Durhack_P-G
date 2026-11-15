$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$receiptPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $receiptPython)) {
    throw 'Project environment missing. Follow README.md to create .venv and install requirements.'
}
& $receiptPython -m streamlit run app.py --server.address 127.0.0.1
exit $LASTEXITCODE
