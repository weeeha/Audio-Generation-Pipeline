# Stops the SFX ComfyUI instance (the python process listening on --port 8189).
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ? { $_.CommandLine -match '--port"? "?8189' } | % { "stopping $($_.ProcessId)"; Stop-Process -Id $_.ProcessId -Force }
Start-Sleep 2
