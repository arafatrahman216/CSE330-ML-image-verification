Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venvCandidates = @(
    (Join-Path $scriptDir ".venv\Scripts\python.exe"),
    (Join-Path $scriptDir "..\.venv\Scripts\python.exe")
)

$venvPython = $venvCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $venvPython) {
    throw "No virtual environment found. Create .venv first, then install requirements."
}

$appHost = if ($env:APP_HOST) { $env:APP_HOST } else { "127.0.0.1" }
$appPort = if ($env:APP_PORT) { $env:APP_PORT } else { "8000" }

& $venvPython -m uvicorn main:app --host $appHost --port $appPort --reload