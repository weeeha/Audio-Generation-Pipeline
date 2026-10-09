# Starts download_higgs_v2.py on the Art PC as a detached process.
# Win32_Process.Create puts the process outside the SSH session's job object,
# so it survives an SSH disconnect (Start-Process would be killed with the session).
#
# Run on the Art PC:  powershell -NoProfile -ExecutionPolicy Bypass -File start-download.ps1

$root = 'G:\models\higgs-audio-v2'
# Any Python with huggingface_hub works; the ACE-Step venv already has 0.36.2.
$python = 'G:\AI\ACE-Step-1.5\.venv\Scripts\python.exe'

New-Item -ItemType Directory -Force $root | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'download_higgs_v2.py') "$root\download_higgs_v2.py" -Force

$cmd = "cmd.exe /c `"set HF_HOME=$root\.hf-home&& $python -u $root\download_higgs_v2.py > $root\download.log 2>&1`""
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cmd}
"pid=$($r.ProcessId) rc=$($r.ReturnValue)  log: $root\download.log"
