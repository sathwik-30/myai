$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python 3.11+ is required."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js/npm is required."
}

$python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "Installing Medha backend dependencies..."
& $python -m pip install -r backend/requirements.txt

Write-Host "Installing Medha frontend dependencies..."
Set-Location (Join-Path $root "frontend")
& npm install

Write-Host ""
Write-Host "Medha is installed."
Write-Host "Launch it with: scripts\Medha.bat"
