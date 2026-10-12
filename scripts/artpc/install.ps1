# install.ps1: set up Qwen3-TTS on the Art PC (CUDA torch + qwen-tts, official bf16 models).
# Idempotent. Needs uv. Installs to G:\AI\Qwen3-TTS, so the G: drive must be mounted.
$ErrorActionPreference = 'Stop'
$Root = 'G:\AI\Qwen3-TTS'
$Py = "$Root\.venv\Scripts\python.exe"

New-Item -ItemType Directory -Force $Root | Out-Null
Set-Location $Root
Copy-Item "$PSScriptRoot\say.py" $Root -Force

if (-not (Test-Path $Py)) { uv venv --python 3.12 .venv }
uv pip install --python $Py torch torchaudio --index-url https://download.pytorch.org/whl/cu128
uv pip install --python $Py qwen-tts==0.1.1 'huggingface_hub[cli]' soundfile

# Xet transfers stalled on this machine (2026-10-08); plain HTTPS downloads do not.
$env:HF_HUB_DISABLE_XET = '1'
foreach ($m in 'Qwen3-TTS-12Hz-1.7B-CustomVoice', 'Qwen3-TTS-12Hz-1.7B-Base') {
    & "$Root\.venv\Scripts\hf.exe" download "Qwen/$m" --local-dir "models\$m"
}

& $Py -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
Write-Host "Installed. Try: $Py $Root\say.py --text 'Hello' --out hello.wav"
