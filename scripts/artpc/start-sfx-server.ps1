# Starts the SFX ComfyUI instance on 127.0.0.1:8189 as a detached process, so it
# survives the SSH session that launched it. Idempotent: does nothing if :8189 answers.
# Uses Krita's ComfyUI code + venv read-only; models, user dir and output are under G:\AI\sfx.
$ErrorActionPreference = 'Stop'
$port = 8189
try {
  Invoke-WebRequest "http://127.0.0.1:$port/system_stats" -UseBasicParsing -TimeoutSec 3 | Out-Null
  "already running on :$port"; exit 0
} catch {}

$py   = "$env:APPDATA\uv\python\cpython-3.12.9-windows-x86_64-none\python.exe"
$sfx  = 'G:\AI\sfx'
$cargs = @(
  '-s', "$sfx\run_comfy.py",
  '--listen', '127.0.0.1', '--port', $port,
  '--extra-model-paths-config', "$sfx\extra_model_paths.yaml",
  '--output-directory', "$sfx\output",
  '--user-directory', "$sfx\user",
  '--disable-auto-launch'
)
$cmd = "cmd /c `"`"$py`" " + (($cargs | ForEach-Object { "`"$_`"" }) -join ' ') + " > `"$sfx\server.log`" 2>&1`""
$r = Invoke-CimMethod Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $sfx }
"started pid $($r.ProcessId); log: $sfx\server.log"

for ($i = 0; $i -lt 90; $i++) {
  Start-Sleep 2
  try { Invoke-WebRequest "http://127.0.0.1:$port/system_stats" -UseBasicParsing -TimeoutSec 3 | Out-Null; "ready on :$port"; exit 0 } catch {}
}
"not answering after 180 s; tail of log:"; Get-Content "$sfx\server.log" -Tail 30
exit 1
