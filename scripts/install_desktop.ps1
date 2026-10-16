# Install a verified staging build and create the branded one-click Desktop shortcut.
param([Parameter(Mandatory = $true)][string]$StageDirectory)
$ErrorActionPreference = 'Stop'
$studioRoot = Split-Path -Parent $PSScriptRoot
$stage = (Resolve-Path -LiteralPath $StageDirectory).Path
$target = [IO.Path]::GetFullPath((Join-Path $studioRoot 'dist\DailyIntelEnglishStudio'))
$pending = [IO.Path]::GetFullPath((Join-Path $studioRoot ('dist\DailyIntelEnglishStudio.next-' + [guid]::NewGuid().ToString('N'))))
$backup = [IO.Path]::GetFullPath((Join-Path $studioRoot ('data\backups\desktop-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))))
foreach ($checkedPath in @($stage, $target, $pending, $backup)) {
    if (-not $checkedPath.StartsWith($studioRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw "Outside workspace: $checkedPath" }
}
if ($stage -eq $target -or -not (Test-Path -LiteralPath (Join-Path $stage 'DailyIntelEnglishStudio.exe') -PathType Leaf) -or -not (Test-Path -LiteralPath (Join-Path $stage '_internal') -PathType Container)) { throw 'A separate verified staging distribution is required.' }
New-Item -ItemType Directory -Force -Path $backup | Out-Null
Copy-Item -LiteralPath $stage -Destination $pending -Recurse
# The locator is relative to the final installed folder, independent of cwd.
$utf8 = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $pending 'studio-runtime.json'), (@{ workspace_dir = '..\..'; data_dir = '..\..\data' } | ConvertTo-Json), $utf8)
$database = Join-Path $studioRoot 'data\app.db'
$upgradePython = Join-Path $studioRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $database -PathType Leaf) {
    & $upgradePython (Join-Path $PSScriptRoot 'desktop_upgrade.py') --database $database --backup (Join-Path $backup 'app.before-upgrade.db')
    if ($LASTEXITCODE -ne 0) { throw 'Database backup/idle-job preflight failed. The installed app was not stopped or replaced.' }
}
$targetExe = Join-Path $target 'DailyIntelEnglishStudio.exe'
$running = Get-CimInstance Win32_Process -Filter "Name = 'DailyIntelEnglishStudio.exe'" | Where-Object { $_.ExecutablePath -eq $targetExe }
if (Test-Path -LiteralPath $database -PathType Leaf) {
    & $upgradePython (Join-Path $PSScriptRoot 'desktop_upgrade.py') --database $database
    if ($LASTEXITCODE -ne 0) { throw 'Studio has unfinished jobs. The installed app was not stopped or replaced.' }
}
foreach ($process in $running) {
    $processHandle = Get-Process -Id $process.ProcessId -ErrorAction Stop
    Stop-Process -Id $process.ProcessId -ErrorAction Stop
    if (-not $processHandle.WaitForExit(20000)) { throw 'The previous Studio process has not exited.' }
}
# Refresh the rollback snapshot after exit so even the last committed idle edit is retained.
if (Test-Path -LiteralPath $database -PathType Leaf) {
    & $upgradePython (Join-Path $PSScriptRoot 'desktop_upgrade.py') --database $database --backup (Join-Path $backup 'app.at-exit.db')
    if ($LASTEXITCODE -ne 0) { throw 'Final database backup failed. The installed distribution was not replaced.' }
}
if (Test-Path -LiteralPath $target) {
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        try { Move-Item -LiteralPath $target -Destination (Join-Path $backup 'DailyIntelEnglishStudio') -ErrorAction Stop; break }
        catch { if ($attempt -eq 19) { throw }; Start-Sleep -Milliseconds 500 }
    }
}
try {
    Move-Item -LiteralPath $pending -Destination $target
} catch {
    if (-not (Test-Path -LiteralPath $target) -and (Test-Path -LiteralPath (Join-Path $backup 'DailyIntelEnglishStudio'))) { Move-Item -LiteralPath (Join-Path $backup 'DailyIntelEnglishStudio') -Destination $target }
    throw
}
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'Daily Beyond English Studio.lnk'
if (Test-Path -LiteralPath $shortcutPath) { Copy-Item -LiteralPath $shortcutPath -Destination (Join-Path $backup 'Desktop-shortcut.lnk') }
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetExe
$shortcut.WorkingDirectory = $studioRoot
$shortcut.IconLocation = "$targetExe,0"
$shortcut.Description = 'Daily Beyond English Studio'
$shortcut.Save()
Write-Host "Installed: $targetExe"
Write-Host "Desktop icon: $shortcutPath"
Write-Host "Previous distribution: $backup"
