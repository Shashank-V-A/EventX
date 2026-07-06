$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "logs"
$LogFile = Join-Path $LogDir "eventx.log"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Main = Join-Path $ProjectRoot "main.py"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "`n=== EventX run at $timestamp ==="

try {
    if (-not (Test-Path $Python)) {
        throw "Python venv not found at $Python. Run: python -m venv .venv && pip install -r requirements.txt"
    }

    Push-Location $ProjectRoot
    $output = & $Python $Main 2>&1 | Out-String
    Add-Content -Path $LogFile -Value $output.TrimEnd()
    $exitCode = $LASTEXITCODE
    Pop-Location

    if ($exitCode -ne 0) {
        Add-Content -Path $LogFile -Value "Exit code: $exitCode"
        exit $exitCode
    }
}
catch {
    Add-Content -Path $LogFile -Value "ERROR: $_"
    exit 1
}
