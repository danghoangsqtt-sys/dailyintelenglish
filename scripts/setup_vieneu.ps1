# Phase 87 (D125): install the local Vietnamese voice (VieNeu-TTS v3 Turbo) in its own environment.
# The app venv is not touched. Creates .venv-vieneu (Python 3.12, CPU / ONNX, no torch) and downloads the model and the
# Whisper "small" model used for word timings into backend\ai\models\vieneu. Safe to run again.
param(
    [switch]$SkipModelDownload
)

# Native tools (uv, pip) write progress to stderr, which Windows PowerShell 5.1 turns into errors under "Stop";
# every step checks $LASTEXITCODE instead.
$ErrorActionPreference = "Continue"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvPath = Join-Path $repoRoot ".venv-vieneu"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"
$hfHome = Join-Path $repoRoot "backend\ai\models\vieneu"
$packages = @("vieneu==3.8.3", "faster-whisper==1.2.1")

$uv = Get-Command uv -ErrorAction SilentlyContinue
# A venv interrupted while being created has python.exe but no pyvenv.cfg; start it again.
if ((Test-Path -LiteralPath $venvPath) -and -not (Test-Path -LiteralPath (Join-Path $venvPath "pyvenv.cfg"))) {
    Remove-Item -LiteralPath $venvPath -Recurse -Force
}
if (-not (Test-Path -LiteralPath $pythonPath)) {
    if ($uv) {
        & uv venv $venvPath --python 3.12
    } else {
        try { & py -3.12 --version | Out-Null } catch { throw "Python 3.12 (or uv) is required. Cai Python 3.12 hoac uv roi chay lai." }
        & py -3.12 -m venv $venvPath
    }
    if ($LASTEXITCODE -ne 0) { throw "Could not create .venv-vieneu. Khong tao duoc .venv-vieneu." }
}

if ($uv) {
    & uv pip install --python $pythonPath @packages
} else {
    & $pythonPath -m pip install --upgrade pip
    & $pythonPath -m pip install @packages
}
if ($LASTEXITCODE -ne 0) { throw "Could not install VieNeu. Khong cai duoc VieNeu." }

if (-not $SkipModelDownload) {
    New-Item -ItemType Directory -Force -Path $hfHome | Out-Null
    $env:HF_HOME = $hfHome
    # ONNX Runtime refuses graph data reached through the hub cache's symlinks (blobs in another folder); store files.
    $env:HF_HUB_DISABLE_SYMLINKS = "1"
    $env:PYTHONIOENCODING = "utf-8"
    # Loading once downloads every file the worker needs; the worker itself then runs offline.
    & $pythonPath -I -c "from vieneu import Vieneu; from faster_whisper import WhisperModel; t = Vieneu(); WhisperModel('small', device='cpu', compute_type='int8'); print(len(t.list_preset_voices()), 'VieNeu voices ready')"
    if ($LASTEXITCODE -ne 0) { throw "Could not download the VieNeu model. Khong tai duoc model VieNeu." }
}

Write-Host "VieNeu is ready: $pythonPath"
Write-Host "Giong Viet VieNeu da san sang."
