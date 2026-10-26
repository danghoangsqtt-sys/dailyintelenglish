param(
    [string]$Version = '2.0.0',
    [string]$OutputDirectory = 'dist/2.0',
    [switch]$Resume
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$output = if ([IO.Path]::IsPathRooted($OutputDirectory)) {
    [IO.Path]::GetFullPath($OutputDirectory)
} else {
    [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
}
if (-not $output.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Package output must be a subdirectory of this workspace.'
}
if (Test-Path -LiteralPath $output) {
    if (-not $Resume) { throw "Refusing to overwrite the versioned package folder: $output" }
    $allowed = @('Full', 'Lite', 'SHA256SUMS.txt')
    $unexpected = @(Get-ChildItem -LiteralPath $output -Force | Where-Object { $_.Name -notin $allowed })
    if ($unexpected.Count) { throw 'Resume folder contains unexpected files; refusing to continue.' }
} else {
    New-Item -ItemType Directory -Path $output | Out-Null
}
$utf8 = New-Object Text.UTF8Encoding($false)
$manifest = @()
foreach ($edition in @('full', 'lite')) {
    $name = (Get-Culture).TextInfo.ToTitleCase($edition)
    $editionRoot = Join-Path $output $name
    $buildRoot = Join-Path $editionRoot 'build'
    $setupRoot = Join-Path $editionRoot 'Setup'
    $app = Join-Path $buildRoot 'DailyIntelEnglishStudio'
    $metadataPath = Join-Path $app 'build-info.json'
    $existingBuildValid = $false
    if (Test-Path -LiteralPath $metadataPath -PathType Leaf) {
        try {
            $existingMetadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
            $existingBuildValid = $existingMetadata.version -eq $Version -and $existingMetadata.edition -eq $edition
        } catch { $existingBuildValid = $false }
    }
    if (-not $existingBuildValid) {
        & (Join-Path $PSScriptRoot 'build_exe.ps1') -OutputRoot $buildRoot -Version $Version -Edition $edition
        if ($LASTEXITCODE -ne 0) { throw "Build failed for $name edition." }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $app '_internal') -PathType Container) -or
        -not (Test-Path -LiteralPath (Join-Path $app 'DailyIntelEnglishStudio.exe') -PathType Leaf) -or
        -not (Test-Path -LiteralPath (Join-Path $app '_internal\backend\db\migrations\040_edge_plain_speech.sql') -PathType Leaf)) {
        throw "$name distribution is missing required runtime files."
    }
    $metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
    if ($metadata.version -ne $Version -or $metadata.edition -ne $edition) {
        throw "$name distribution metadata does not match $Version/$edition."
    }

    New-Item -ItemType Directory -Force -Path $setupRoot | Out-Null
    $setupApp = Join-Path $setupRoot 'DailyIntelEnglishStudio'
    if (-not (Test-Path -LiteralPath (Join-Path $setupApp 'DailyIntelEnglishStudio.exe') -PathType Leaf)) {
        Copy-Item -LiteralPath $app -Destination $setupRoot -Recurse
    }
    $instructions = @"
Daily Beyond English Studio $Version — $name edition

This archive contains the complete Windows x64 application folder. Extract it into
the data/tmp/desktop-download folder of the matching project workspace, then install
from the project root with:

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_desktop.ps1 -StageDirectory .\data\tmp\desktop-download\DailyIntelEnglishStudio

Follow docs/user/windows-installation.md for the renderer, Node.js and FFmpeg setup.
The Full edition enables local picture controls when compatible GPU/model components
are present; Lite hides those controls. Speech uses Edge TTS only. Script emotion
insertion and local speech-engine selection have been removed by owner request.
See docs/operations/edge-plain-speech.md for existing-project migration guidance.
"@
    [IO.File]::WriteAllText((Join-Path $setupRoot 'SETUP.txt'), $instructions, $utf8)
    $zip = Join-Path $output "DailyBeyondEnglishStudio-$Version-$name-windows-x64.zip"
    & (Join-Path $root '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'create_setup_zip.py') $setupRoot $zip
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $zip -PathType Leaf)) { throw "ZIP creation failed for $name." }
    $hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
    $manifest += "$hash  $(Split-Path -Leaf $zip)"
    Write-Host "Packaged $name`: $zip ($hash)"
}

[IO.File]::WriteAllLines((Join-Path $output 'SHA256SUMS.txt'), $manifest, $utf8)
Write-Host "Version $Version packages and checksums: $output"
