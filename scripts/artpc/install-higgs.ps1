# install-higgs.ps1: set up Higgs Audio v2 (Higgs TTS 2) generation on the Art PC.
# Idempotent. Needs uv. Code and venv go to G:\AI\higgs-tts; the model files are already in
# G:\models\higgs-audio-v2 (download: docs/models.md). The G: drive must be mounted.
#
# Run on the Art PC:  powershell -NoProfile -ExecutionPolicy Bypass -File install-higgs.ps1
$ErrorActionPreference = 'Stop'
$Root = 'G:\AI\higgs-tts'
$Py = "$Root\.venv\Scripts\python.exe"

New-Item -ItemType Directory -Force $Root | Out-Null
Set-Location $Root
Copy-Item "$PSScriptRoot\higgs.py" $Root -Force

if (-not (Test-Path $Py)) { uv venv --python 3.12 .venv }
# Same torch build as G:\AI\Qwen3-TTS, so uv links it from its cache instead of downloading 3 GB again.
# torchaudio is required: transformers' HiggsAudioV2TokenizerModel refuses to load without it.
uv pip install --python $Py torch==2.11.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cu128
# The downloaded model folders are in the Transformers-native format (HiggsAudioV2ForConditionalGeneration,
# transformers >= 5.3.0), so Boson's older boson_multimodal package does not load them.
# No torchcodec (on Windows it needs shared FFmpeg DLLs): higgs.py loads reference clips with librosa itself.
uv pip install --python $Py transformers==5.17.0 accelerate soundfile librosa

& $Py -c "import torch, transformers; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), 'transformers', transformers.__version__)"
Write-Host "Installed. Try: $Py $Root\higgs.py --text 'Hello' --out hello.wav --free-gpu"
