# Lease guard for start-music-server.ps1. Started detached when it pauses llama-server: after
# -Minutes, if the pause marker still carries this session's -Token, the client never cleaned up
# (crashed, killed, lost its SSH session), so run stop-music-server.ps1 to stop ACE-Step and
# resume llama-server. A normal stop removes the marker first, and the guard then does nothing.
# Added after 2026-10-12, when a killed client left llama-server paused for about 80 minutes.
param([Parameter(Mandatory)][string]$Token, [int]$Minutes = 30)
$dir    = 'G:\AI\music'
$marker = "$dir\paused-llama.txt"
Start-Sleep -Seconds ($Minutes * 60)
if ((Test-Path $marker) -and ((Get-Content $marker -Raw) -match [regex]::Escape($Token))) {
  "$(Get-Date -Format s) lease $Token expired after $Minutes min; stopping ACE-Step and resuming llama-server" |
    Add-Content "$dir\guard.log"
  & "$dir\stop-music-server.ps1" *>> "$dir\guard.log"
}
