# Build a standalone Windows .exe via PyInstaller (Task 12.2).
#
# Usage: powershell -File scripts\build_exe.ps1
param(
    [string]$OutputRoot = 'dist',
    [string]$Version = '1.6.0',
    # Phase 71 (ENH-053): 'lite' hides the local AI picture features by default (for computers without a large GPU)
    [ValidateSet('full', 'lite')][string]$Edition = 'full'
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$buildOutputRoot = if ([IO.Path]::IsPathRooted($OutputRoot)) { [IO.Path]::GetFullPath($OutputRoot) } else { [IO.Path]::GetFullPath((Join-Path $root $OutputRoot)) }
if (-not $buildOutputRoot.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Build output must be a subdirectory of this workspace.'
}
$appDir = Join-Path $buildOutputRoot 'DailyIntelEnglishStudio'
$appExe = Join-Path $appDir 'DailyIntelEnglishStudio.exe'
if (Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $appExe }) {
    throw 'This build is running. Build into a staging directory, then install it.'
}

& "$root\.venv\Scripts\pip.exe" show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing pyinstaller..."
    & "$root\.venv\Scripts\pip.exe" install pyinstaller
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller installation failed.' }
}

& npm --prefix renderer ci
if ($LASTEXITCODE -ne 0) { throw 'Renderer dependency installation failed.' }
& npm --prefix renderer run typecheck
if ($LASTEXITCODE -ne 0) { throw 'Renderer typecheck failed.' }
& npm --prefix renderer run build:preview
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath "$root\frontend\static\solo-preview\player.js" -PathType Leaf)) {
    throw 'Solo preview bundle build failed.'
}
Push-Location (Join-Path $root 'renderer')
try {
    & npx remotion browser ensure
    if ($LASTEXITCODE -ne 0) { throw 'Remotion browser preparation failed.' }
} finally {
    Pop-Location
}
& "$root\.venv\Scripts\pyinstaller.exe" daily_intel_english_studio.spec --noconfirm --distpath $buildOutputRoot
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $appExe -PathType Leaf)) { throw 'EXE build failed.' }
$relativeWorkspace = & "$root\.venv\Scripts\python.exe" -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' $root $appDir
if ($LASTEXITCODE -ne 0) { throw 'Runtime locator generation failed.' }
$runtime = @{ workspace_dir = $relativeWorkspace; data_dir = (Join-Path $relativeWorkspace 'data') }
$utf8 = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $appDir 'studio-runtime.json'), ($runtime | ConvertTo-Json), $utf8)
$metadata = @{ version = $Version; edition = $Edition; built_at_utc = [DateTime]::UtcNow.ToString('o'); source_commit = ((& git rev-parse HEAD) -join ''); source_dirty = [bool](& git status --porcelain) }
[IO.File]::WriteAllText((Join-Path $appDir 'build-info.json'), ($metadata | ConvertTo-Json), $utf8)
[IO.File]::WriteAllText((Join-Path $appDir 'START-HERE.txt'), "Daily Beyond English Studio $Version ($Edition edition)`r`n`r`nPlace this complete folder under the repository's dist directory.`r`nDouble-click DailyIntelEnglishStudio.exe, or run scripts/install_desktop.ps1 to create a Desktop icon.`r`nKeep _internal and studio-runtime.json beside the EXE. The local renderer, Node.js, ffmpeg and existing image environment remain in the repository.`r`nProject data: ../../data. Startup log: ../../data/logs/desktop.log.`r`n", $utf8)

Write-Host ""
Write-Host "Build complete: $appExe"
