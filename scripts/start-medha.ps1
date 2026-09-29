$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py app\launcher\launcher.py
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python app\launcher\launcher.py
    exit $LASTEXITCODE
}

Write-Host "Python was not found. Install Python 3.11+ and run Medha again."
exit 1
