param(
    [switch]$SkipModelDownload,
    [string]$ModelPath = $env:DIE_OMNIVOICE_MODEL_PATH
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvPath = Join-Path $repoRoot ".venv-omnivoice"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"
if ([string]::IsNullOrWhiteSpace($ModelPath)) {
    $ModelPath = Join-Path $repoRoot "data\models\omnivoice"
}
$modelPath = [IO.Path]::GetFullPath($ModelPath)

try {
    & py -3.11 --version | Out-Null
} catch {
    throw "Python 3.11 is required for the isolated OmniVoice environment. Install Python 3.11 and rerun this script."
}
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.11 is required for the isolated OmniVoice environment. Install Python 3.11 and rerun this script."
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    & py -3.11 -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { throw "Could not create .venv-omnivoice with Python 3.11." }
}

& $pythonPath -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Could not upgrade pip in .venv-omnivoice." }

# Follow OmniVoice's CUDA 12.8 installation guidance. App and image environments stay intact.
& $pythonPath -m pip install "torch==2.8.0+cu128" "torchaudio==2.8.0+cu128" --extra-index-url "https://download.pytorch.org/whl/cu128"
if ($LASTEXITCODE -ne 0) { throw "Could not install the CUDA 12.8 PyTorch wheels." }
& $pythonPath -m pip install -r (Join-Path $repoRoot "backend\ai\tts\omnivoice-requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Could not install OmniVoice dependencies." }

$cudaCheck = & $pythonPath -c "import torch; print(torch.cuda.is_available())"
if ($LASTEXITCODE -ne 0 -or $cudaCheck.Trim() -ne "True") {
    throw "OmniVoice dependencies installed, but CUDA is unavailable in the dedicated environment. Check the NVIDIA driver before downloading model weights."
}

if (-not $SkipModelDownload) {
    New-Item -ItemType Directory -Force -Path $modelPath | Out-Null
    $encodedPath = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($modelPath))
    $downloadCode = "import base64; from huggingface_hub import snapshot_download; snapshot_download(repo_id='k2-fsa/OmniVoice', local_dir=base64.b64decode('$encodedPath').decode('utf-8'))"
    & $pythonPath -c $downloadCode
    if ($LASTEXITCODE -ne 0) { throw "OmniVoice model download failed. Rerun this script after restoring Hugging Face network access." }
}

Write-Host "OmniVoice isolated setup is ready. Model path: $modelPath"
