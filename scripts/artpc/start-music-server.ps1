# Starts ACE-Step's API server on 127.0.0.1:8001 as a detached process, so it survives the SSH
# session that launched it. Idempotent: does nothing if :8001 answers. stop-music-server.ps1 undoes it.
#
# -FreeGpu pauses llama-server first: through the llama-hold watcher's flag file when that task runs
# (a plain schtasks /end is undone within seconds), otherwise by ending the llama-server task.
# ACE-Step sizes itself from the card's total memory, so MAX_CUDA_VRAM passes what nvidia-smi
# reports as free: about 23 GB with llama-server paused (full model, 1.7B planner, XL fits).
# Next to llama-server only about 2 GB is free, and even ACE-Step's smallest mode runs out of
# memory loading the model there (2026-10-12), so the script refuses to start below 8 GB.
param([string]$Model = 'acestep-v15-turbo', [switch]$FreeGpu)
$ErrorActionPreference = 'Stop'
$port   = 8001
$ace    = 'G:\AI\ACE-Step-1.5'
$dir    = 'G:\AI\music'
$flag   = 'C:\Users\mvyho\llama-hold.manual'
$marker = "$dir\paused-llama.txt"   # how this script paused llama-server, read by stop-music-server.ps1

function Free { [int](nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits) }
function Answers($url) { try { Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 3 | Out-Null; $true } catch { $false } }

New-Item -ItemType Directory -Force $dir | Out-Null
if (Answers "http://127.0.0.1:$port/v1/models") { "already running on :$port"; exit 0 }

if ($FreeGpu -and (Answers 'http://127.0.0.1:8080/health')) {
  if ((schtasks /query /tn llama-hold /fo csv /nh) -match '"Running"') {
    New-Item -ItemType File -Force $flag | Out-Null
    Set-Content $marker 'hold'
  } else {
    schtasks /end /tn llama-server | Out-Null
    Set-Content $marker 'task'
  }
  $t = Get-Date
  do { Start-Sleep 1 } until ((Free) -gt 20000 -or ((Get-Date) - $t).TotalSeconds -gt 60)
  "paused llama-server ($(Get-Content $marker)); $(Free) MiB free"
}

$freeGb = [math]::Floor((Free) / 1024)
if ($freeGb -lt 8) {
  "only $freeGb GB of VRAM free; ACE-Step does not fit next to llama-server. Rerun with -FreeGpu (music.py --free-gpu)."
  exit 1
}
$settings = "set MAX_CUDA_VRAM=$freeGb&& set ACESTEP_CONFIG_PATH=$Model&& set ACESTEP_LM_MODEL_PATH=acestep-5Hz-lm-1.7B" +
            "&& set ACESTEP_INIT_LLM=auto&& set TOKENIZERS_PARALLELISM=false" +
            # Load the models at startup: lazy loading from the G: USB disk inside the first request
            # blocks the server for over a minute, and every API call times out meanwhile.
            "&& set ACESTEP_NO_INIT=false"
$cmd = "cmd /c `"$settings&& `"$ace\.venv\Scripts\acestep-api.exe`" --host 127.0.0.1 --port $port > `"$dir\server.log`" 2>&1`""
$r = Invoke-CimMethod Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $ace }
"started pid $($r.ProcessId) with $Model, MAX_CUDA_VRAM=$freeGb; log: $dir\server.log"

$t = Get-Date
while (((Get-Date) - $t).TotalSeconds -lt 600) {
  Start-Sleep 3
  if (Answers "http://127.0.0.1:$port/v1/models") { "ready on :$port after $([int]((Get-Date) - $t).TotalSeconds) s"; exit 0 }
}
"not answering after 600 s; tail of log:"; Get-Content "$dir\server.log" -Tail 30
exit 1
