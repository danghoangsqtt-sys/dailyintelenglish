# Build a standalone Windows .exe via PyInstaller (Task 12.2).
#
# Usage: powershell -File scripts\build_exe.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

& "$root\venv\Scripts\pip.exe" show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing pyinstaller..."
    & "$root\venv\Scripts\pip.exe" install pyinstaller
}

& "$root\venv\Scripts\pyinstaller.exe" daily_intel_english_studio.spec --noconfirm

Write-Host ""
Write-Host "Build complete: $root\dist\DailyIntelEnglishStudio\DailyIntelEnglishStudio.exe"
