1..4 | ForEach-Object {
    Start-Process powershell.exe "-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"C:\Antigravity\Profiles\Worker_$_\Start-Worker.ps1`""
    Start-Sleep -Seconds 1
}
