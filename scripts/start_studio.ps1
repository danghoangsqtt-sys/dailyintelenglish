# Run the current workspace source, including the episode title/folder fixes.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\start_studio.ps1
param([ValidateRange(1024, 65535)][int]$Port = 8001)

$ErrorActionPreference = 'Stop'
$studioRoot = Split-Path -Parent $PSScriptRoot
$studioPython = Join-Path $studioRoot '.venv\Scripts\python.exe'
$studioData = Join-Path $studioRoot 'data'
if (-not (Test-Path -LiteralPath $studioPython -PathType Leaf)) {
    throw 'The workspace Python environment is missing. Install the project dependencies first.'
}
if (-not (Test-Path -LiteralPath (Join-Path $studioRoot 'renderer\node_modules') -PathType Container)) {
    throw 'Renderer dependencies are missing. Run npm ci in renderer first.'
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Node.js is required for video rendering.'
}
if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) {
    throw "Port $Port is already in use. Open the existing source session or select another -Port."
}

# SQLite's backup API includes committed WAL contents and leaves the source DB unchanged.
$studioDb = Join-Path $studioData 'app.db'
if (Test-Path -LiteralPath $studioDb -PathType Leaf) {
    $studioBackups = Join-Path $studioData 'backups'
    New-Item -ItemType Directory -Force -Path $studioBackups | Out-Null
    $studioBackup = Join-Path $studioBackups ("before-source-start-{0}-{1}.db" -f (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0, 8)))
    $studioBackupCode = @'
import sqlite3
import sys
from pathlib import Path
with sqlite3.connect(Path(sys.argv[1]).resolve().as_uri() + "?mode=ro", uri=True) as source:
    with sqlite3.connect(sys.argv[2]) as target:
        source.backup(target)
'@
    $studioBackupCode | & $studioPython - $studioDb $studioBackup
    if ($LASTEXITCODE -ne 0) { throw 'Database backup failed; the application was not started.' }
    Write-Host "Database backup: $studioBackup"
}

$studioOldHost = $env:DIE_APP_HOST
$studioOldPort = $env:DIE_APP_PORT
$studioOldData = $env:DIE_DATA_DIR
Push-Location $studioRoot
try {
    $env:DIE_APP_HOST = 'localhost'
    $env:DIE_APP_PORT = [string]$Port
    $env:DIE_DATA_DIR = $studioData
    Write-Host "Current source: http://localhost:$Port (workspace data: $studioData)"
    & $studioPython -m backend.desktop_launcher
    if ($LASTEXITCODE -ne 0) { throw "Studio exited with code $LASTEXITCODE." }
} finally {
    $env:DIE_APP_HOST = $studioOldHost
    $env:DIE_APP_PORT = $studioOldPort
    $env:DIE_DATA_DIR = $studioOldData
    Pop-Location
}
