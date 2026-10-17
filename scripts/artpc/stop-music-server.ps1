# Stops the ACE-Step API server started by start-music-server.ps1, then resumes llama-server if that
# script paused it. Safe to run when nothing is running.
$dir    = 'G:\AI\music'
$flag   = 'C:\Users\mvyho\llama-hold.manual'
$marker = "$dir\paused-llama.txt"

Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'acestep-api' -and $_.Name -eq 'cmd.exe' } |
  ForEach-Object { "stopping $($_.ProcessId)"; taskkill /F /T /PID $_.ProcessId | Out-Null }
# The console-script launcher may outlive its cmd wrapper.
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'acestep-api' -and $_.Name -ne 'powershell.exe' } |
  ForEach-Object { taskkill /F /T /PID $_.ProcessId 2>$null | Out-Null }

if (Test-Path $marker) {
  # Let the GPU memory come free first, so llama-server does not load into a full card.
  $t = Get-Date
  do { Start-Sleep 1 } until ([int](nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits) -gt 20000 -or ((Get-Date) - $t).TotalSeconds -gt 30)
  $how = ((Get-Content $marker).Trim() -split ' ')[0]   # 'hold <token>' or 'task <token>'
  if ($how -eq 'hold') { Remove-Item $flag -ErrorAction SilentlyContinue } else { schtasks /run /tn llama-server | Out-Null }
  Remove-Item $marker
  "resumed llama-server ($how)"
}
