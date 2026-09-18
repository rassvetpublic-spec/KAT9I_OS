# C:\Antigravity\ANTIGRAVITY-MULTI.ps1
$ErrorActionPreference = 'SilentlyContinue'
$RootDir = "C:\Antigravity"
$LogFile = Join-Path $RootDir "_System\Logs\startup_trace.log"
if (-not (Test-Path (Join-Path $RootDir "_System\Logs"))) { New-Item -ItemType Directory (Join-Path $RootDir "_System\Logs") -Force | Out-Null }

function Write-StartLog($msg) {
    $time = Get-Date -Format "HH:mm:ss.fff"
    "$time $msg" | Out-File -FilePath $LogFile -Append -Encoding UTF8
    Write-Host $msg -ForegroundColor Green
}

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Collections.Generic;

public class WinAPI {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern bool SetWindowText(IntPtr hWnd, string text);

    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);

    [DllImport("user32.dll")]
    public static extern bool SystemParametersInfo(uint uiAction, uint uiParam, out RECT pvParam, uint fWinIni);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    public static List<IntPtr> GetWindowsForPids(uint[] pids) {
        var list = new List<IntPtr>();
        var pidSet = new HashSet<uint>(pids);
        EnumWindows((hWnd, lParam) => {
            if (IsWindowVisible(hWnd)) {
                uint pid;
                GetWindowThreadProcessId(hWnd, out pid);
                if (pidSet.Contains(pid)) {
                    list.Add(hWnd);
                }
            }
            return true;
        }, IntPtr.Zero);
        return list;
    }
}
"@

function Get-RunningWorkersCount {
    # Count isolated worker profiles safely
    $wmiProcs = Get-CimInstance Win32_Process -Filter "Name = 'antigravity.exe'" -ErrorAction SilentlyContinue
    $count = 0
    foreach ($p in $wmiProcs) {
        if ($p.CommandLine -match '--user-data-dir=.*Worker_') {
            $count++
        }
    }
    return $count
}

function Check-Manager {
    $isPortUp = [bool](Get-NetTCPConnection -LocalPort 8045 -State Listen -ErrorAction SilentlyContinue)
    if (-not $isPortUp) {
        Write-StartLog "AG Manager is NOT running (Port 8045 not listening). Auto-starting..."
        $managerCmd = Join-Path $RootDir "_Manager\Start-Manager.cmd"
        if (Test-Path $managerCmd) {
            Start-Process -FilePath $managerCmd -WindowStyle Hidden
        } else {
            $toolsExe = Join-Path $RootDir "_Manager\antigravity-tools.exe"
            if (Test-Path $toolsExe) {
                Start-Process -FilePath $toolsExe -WorkingDirectory (Join-Path $RootDir "_Manager") -WindowStyle Hidden
            } else {
                Write-StartLog "Cannot find Manager executable at $toolsExe or $managerCmd"
            }
        }
    } else {
        Write-StartLog "AG Manager is already running on port 8045."
    }
}

function Run-Diagnostic {
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "          DIAGNOSTIC MODE                " -ForegroundColor Yellow
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-StartLog "--- DIAGNOSTIC MODE STARTED ---"
    
    Write-Host "Traffic path: Local Script -> Happ (SOCKS5 127.0.0.1:10808) -> PIA -> External" -ForegroundColor Gray
    
    $piaCtl = "C:\Program Files\Private Internet Access\piactl.exe"
    if (Test-Path $piaCtl) {
        $piaState = & $piaCtl get connectionstate
        Write-Host "PIA Status: $piaState" -ForegroundColor $(if($piaState -eq 'Connected') {'Green'} else {'Red'})
        Write-StartLog "PIA Status: $piaState"
    } else {
        Write-Host "PIA not found at standard path." -ForegroundColor Red
        Write-StartLog "PIA not found."
    }

    $happPort = Get-NetTCPConnection -LocalPort 10808 -State Listen -ErrorAction SilentlyContinue
    if ($happPort) {
        Write-Host "Happ SOCKS5 Proxy: LISTENING on 10808" -ForegroundColor Green
        Write-StartLog "Happ SOCKS5 Proxy: LISTENING on 10808"
        # Detailed active connections to proxy
        $activeConns = Get-NetTCPConnection -LocalPort 10808 -State Established -ErrorAction SilentlyContinue
        if ($activeConns) {
            Write-Host "Active Connections to Happ Proxy:" -ForegroundColor Cyan
            $activeConns | Format-Table LocalAddress, LocalPort, RemoteAddress, RemotePort, State | Out-String | Write-Host
            Write-StartLog "Active connections found: $($activeConns.Count)"
        }
    } else {
        Write-Host "Happ SOCKS5 Proxy: NOT LISTENING (Port 10808)" -ForegroundColor Red
        Write-StartLog "Happ SOCKS5 Proxy: NOT LISTENING"
    }
    
    Write-Host "Check complete. Review log at $LogFile" -ForegroundColor Cyan
    Read-Host "Press Enter to continue..."
}

function Run-Doctor {
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "             DOCTOR MODE                 " -ForegroundColor Yellow
    Write-Host "=========================================" -ForegroundColor Cyan
    
    # 1. Desktop and Start Menu Shortcuts
    Write-Host "`n[1] Checking Shortcuts..." -ForegroundColor Yellow
    $wshell = New-Object -ComObject WScript.Shell
    foreach ($loc in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
        $shortcutPath = Join-Path $loc "Antigravity Multi.lnk"
        $shortcut = $wshell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = "pwsh.exe"
        $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$RootDir\ANTIGRAVITY-MULTI.ps1`""
        $shortcut.IconLocation = "$RootDir\antigravity.ico"
        $shortcut.Save()
        Write-Host " Fixed shortcut at: $shortcutPath" -ForegroundColor Green
    }

    # 2. Context Menu
    Write-Host "`n[2] Checking Context Menu..." -ForegroundColor Yellow
    $regPath = "HKCU:\Software\Classes\Directory\Background\shell\Antigravity"
    if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }
    Set-ItemProperty -Path $regPath -Name "MUIVerb" -Value "Launch Antigravity"
    Set-ItemProperty -Path $regPath -Name "Icon" -Value "$RootDir\antigravity.ico"
    $cmdPath = "$regPath\command"
    if (-not (Test-Path $cmdPath)) { New-Item -Path $cmdPath -Force | Out-Null }
    Set-ItemProperty -Path $cmdPath -Name "(Default)" -Value "pwsh.exe -NoProfile -ExecutionPolicy Bypass -File `"$RootDir\ANTIGRAVITY-MULTI.ps1`""
    Write-Host " Fixed context menu (Right-click in Explorer)." -ForegroundColor Green

    # 3. PIA/Happ Config Backup & Check
    Write-Host "`n[3] Checking PIA/Happ Split Tunneling Settings..." -ForegroundColor Yellow
    Write-Host " EXPECTED: Split Tunneling Enabled. 'C:/Program Files/FlyFrogLLC/Happ/core/xray.exe' -> Bypass VPN" -ForegroundColor Gray
    $piaSettingsPath = "C:\Program Files\Private Internet Access\data\settings.json"
    if (Test-Path $piaSettingsPath) {
        $settingsRaw = Get-Content -Raw $piaSettingsPath
        $settings = $settingsRaw | ConvertFrom-Json
        $xrayRule = $settings.splitTunnelRules | Where-Object { $_.mode -eq 'exclude' -and ($_.path -replace '\\','/') -eq 'C:/Program Files/FlyFrogLLC/Happ/core/xray.exe' }
        if (-not $settings.splitTunnelEnabled -or -not $xrayRule) {
            Write-Host " WARNING: PIA Split Tunneling for Happ is NOT correctly configured!" -ForegroundColor Red
            $fix = Read-Host " Do you want to Auto-Fix it? (Y/N)"
            if ($fix -match 'Y') {
                $bakPath = "$piaSettingsPath.bak_$(Get-Date -f 'yyyyMMdd_HHmmss')"
                Copy-Item $piaSettingsPath $bakPath -Force
                Write-Host " Backed up PIA settings to $bakPath" -ForegroundColor Green
                
                $settings.splitTunnelEnabled = $true
                if (-not $xrayRule) {
                    $newRule = @{
                        id = [guid]::NewGuid().ToString()
                        mode = "exclude"
                        path = "C:\Program Files\FlyFrogLLC\Happ\core\xray.exe"
                        type = "app"
                    }
                    $settings.splitTunnelRules += $newRule
                }
                $settings | ConvertTo-Json -Depth 10 | Set-Content $piaSettingsPath
                Write-Host " PIA settings fixed. Please restart PIA." -ForegroundColor Green
            }
        } else {
            Write-Host " PIA Split Tunneling for Happ is configured correctly." -ForegroundColor Green
        }
    } else {
        Write-Host " PIA settings.json not found." -ForegroundColor Red
    }

    # 4. Worker Paths and Child Scripts Correctness
    Write-Host "`n[4] Checking Workers Paths and Child Scripts..." -ForegroundColor Yellow
    1..4 | ForEach-Object {
        $wPath = Join-Path $RootDir "Profiles\Worker_$_"
        if (-not (Test-Path $wPath)) {
            New-Item -Path $wPath -ItemType Directory -Force | Out-Null
            Write-Host " Created missing Worker $_ folder." -ForegroundColor Yellow
        } else {
            Write-Host " Worker $_ folder exists." -ForegroundColor Green
        }
        $childScript = Join-Path $wPath "Start-Worker.ps1"
        if (Test-Path $childScript) {
            $content = Get-Content $childScript -Raw
            if ($content -match "(?i)Stop-Process\s+-Name\s+Antigravity") {
                Write-Host " WARNING: Found dangerous 'kill process' in Worker $_ script! Fixing..." -ForegroundColor Red
                $content = $content -replace "(?i)Stop-Process\s+-Name\s+Antigravity.*", "# [Removed dangerous Stop-Process]"
                $content | Set-Content $childScript
                Write-Host " Fixed script: $childScript" -ForegroundColor Green
            } else {
                Write-Host " Script $childScript is safe (no blind kill process)." -ForegroundColor Green
            }
        } else {
            Write-Host " WARNING: $childScript is missing!" -ForegroundColor Red
        }
    }

    # 5. Junction link verification
    Write-Host "`n[5] Checking Junction/Hardlink..." -ForegroundColor Yellow
    $TargetGemini = "C:\GIT\AGY\.gemini"
    $CommonGemini = "$RootDir\Common\.gemini"
    
    if (Test-Path $TargetGemini) {
        Write-Host " Target path $TargetGemini exists." -ForegroundColor Green
        
        $item = Get-Item $CommonGemini -ErrorAction SilentlyContinue
        if ($item -and $item.LinkType -eq 'Junction') {
            Write-Host " Junction $CommonGemini -> $($item.Target) is CORRECT." -ForegroundColor Green
        } else {
            Write-Host " WARNING: $CommonGemini is NOT a junction! You should run Setup-Junction.ps1." -ForegroundColor Red
        }
    } else {
        Write-Host " WARNING: Target path $TargetGemini is MISSING!" -ForegroundColor Red
    }

    Write-Host "`nDoctor checks complete!" -ForegroundColor Cyan
    Read-Host "Press Enter to continue..."
}

function Sync-StandaloneApp {
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "             UPDATE MODE                 " -ForegroundColor Yellow
    Write-Host "=========================================" -ForegroundColor Cyan
    $source = "C:\GIT\AGY\app"
    $target = "C:\Antigravity\Standalone\App"
    
    if (Test-Path $source) {
        Write-Host "Syncing Antigravity binaries from main installation to Standalone..." -ForegroundColor Yellow
        # Stop workers if running to unlock files
        Get-CimInstance Win32_Process -Filter "Name = 'antigravity.exe'" | Where-Object { # C:\Antigravity\ANTIGRAVITY-MULTI.ps1
$ErrorActionPreference = 'SilentlyContinue'
$RootDir = "C:\Antigravity"
$LogFile = Join-Path $RootDir "_System\Logs\startup_trace.log"
if (-not (Test-Path (Join-Path $RootDir "_System\Logs"))) { New-Item -ItemType Directory (Join-Path $RootDir "_System\Logs") -Force | Out-Null }

function Write-StartLog($msg) {
    $time = Get-Date -Format "HH:mm:ss.fff"
    "$time $msg" | Out-File -FilePath $LogFile -Append -Encoding UTF8
    Write-Host $msg -ForegroundColor Green
}

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Collections.Generic;

public class WinAPI {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern bool SetWindowText(IntPtr hWnd, string text);

    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);

    [DllImport("user32.dll")]
    public static extern bool SystemParametersInfo(uint uiAction, uint uiParam, out RECT pvParam, uint fWinIni);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    public static List<IntPtr> GetWindowsForPids(uint[] pids) {
        var list = new List<IntPtr>();
        var pidSet = new HashSet<uint>(pids);
        EnumWindows((hWnd, lParam) => {
            if (IsWindowVisible(hWnd)) {
                uint pid;
                GetWindowThreadProcessId(hWnd, out pid);
                if (pidSet.Contains(pid)) {
                    list.Add(hWnd);
                }
            }
            return true;
        }, IntPtr.Zero);
        return list;
    }
}
"@

function Get-RunningWorkersCount {
    # Count isolated worker profiles safely
    $wmiProcs = Get-CimInstance Win32_Process -Filter "Name = 'antigravity.exe'" -ErrorAction SilentlyContinue
    $count = 0
    foreach ($p in $wmiProcs) {
        if ($p.CommandLine -match '--user-data-dir=.*Worker_') {
            $count++
        }
    }
    return $count
}

function Check-Manager {
    $isPortUp = [bool](Get-NetTCPConnection -LocalPort 8045 -State Listen -ErrorAction SilentlyContinue)
    if (-not $isPortUp) {
        Write-StartLog "AG Manager is NOT running (Port 8045 not listening). Auto-starting..."
        $managerCmd = Join-Path $RootDir "_Manager\Start-Manager.cmd"
        if (Test-Path $managerCmd) {
            Start-Process -FilePath $managerCmd -WindowStyle Hidden
        } else {
            $toolsExe = Join-Path $RootDir "_Manager\antigravity-tools.exe"
            if (Test-Path $toolsExe) {
                Start-Process -FilePath $toolsExe -WorkingDirectory (Join-Path $RootDir "_Manager") -WindowStyle Hidden
            } else {
                Write-StartLog "Cannot find Manager executable at $toolsExe or $managerCmd"
            }
        }
    } else {
        Write-StartLog "AG Manager is already running on port 8045."
    }
}

function Run-Diagnostic {
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "          DIAGNOSTIC MODE                " -ForegroundColor Yellow
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-StartLog "--- DIAGNOSTIC MODE STARTED ---"
    
    Write-Host "Traffic path: Local Script -> Happ (SOCKS5 127.0.0.1:10808) -> PIA -> External" -ForegroundColor Gray
    
    $piaCtl = "C:\Program Files\Private Internet Access\piactl.exe"
    if (Test-Path $piaCtl) {
        $piaState = & $piaCtl get connectionstate
        Write-Host "PIA Status: $piaState" -ForegroundColor $(if($piaState -eq 'Connected') {'Green'} else {'Red'})
        Write-StartLog "PIA Status: $piaState"
    } else {
        Write-Host "PIA not found at standard path." -ForegroundColor Red
        Write-StartLog "PIA not found."
    }

    $happPort = Get-NetTCPConnection -LocalPort 10808 -State Listen -ErrorAction SilentlyContinue
    if ($happPort) {
        Write-Host "Happ SOCKS5 Proxy: LISTENING on 10808" -ForegroundColor Green
        Write-StartLog "Happ SOCKS5 Proxy: LISTENING on 10808"
        # Detailed active connections to proxy
        $activeConns = Get-NetTCPConnection -LocalPort 10808 -State Established -ErrorAction SilentlyContinue
        if ($activeConns) {
            Write-Host "Active Connections to Happ Proxy:" -ForegroundColor Cyan
            $activeConns | Format-Table LocalAddress, LocalPort, RemoteAddress, RemotePort, State | Out-String | Write-Host
            Write-StartLog "Active connections found: $($activeConns.Count)"
        }
    } else {
        Write-Host "Happ SOCKS5 Proxy: NOT LISTENING (Port 10808)" -ForegroundColor Red
        Write-StartLog "Happ SOCKS5 Proxy: NOT LISTENING"
    }
    
    Write-Host "Check complete. Review log at $LogFile" -ForegroundColor Cyan
    Read-Host "Press Enter to continue..."
}

function Run-Doctor {
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "             DOCTOR MODE                 " -ForegroundColor Yellow
    Write-Host "=========================================" -ForegroundColor Cyan
    
    # 1. Desktop and Start Menu Shortcuts
    Write-Host "`n[1] Checking Shortcuts..." -ForegroundColor Yellow
    $wshell = New-Object -ComObject WScript.Shell
    foreach ($loc in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
        $shortcutPath = Join-Path $loc "Antigravity Multi.lnk"
        $shortcut = $wshell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = "pwsh.exe"
        $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RootDir\ANTIGRAVITY-MULTI.ps1`""
        $shortcut.IconLocation = "$RootDir\antigravity.ico"
        $shortcut.Save()
        Write-Host " Fixed shortcut at: $shortcutPath" -ForegroundColor Green
    }

    # 2. Context Menu
    Write-Host "`n[2] Checking Context Menu..." -ForegroundColor Yellow
    $regPath = "HKCU:\Software\Classes\Directory\Background\shell\Antigravity"
    if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }
    Set-ItemProperty -Path $regPath -Name "MUIVerb" -Value "Launch Antigravity"
    Set-ItemProperty -Path $regPath -Name "Icon" -Value "$RootDir\antigravity.ico"
    $cmdPath = "$regPath\command"
    if (-not (Test-Path $cmdPath)) { New-Item -Path $cmdPath -Force | Out-Null }
    Set-ItemProperty -Path $cmdPath -Name "(Default)" -Value "pwsh.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RootDir\ANTIGRAVITY-MULTI.ps1`""
    Write-Host " Fixed context menu (Right-click in Explorer)." -ForegroundColor Green

    # 3. PIA/Happ Config Backup & Check
    Write-Host "`n[3] Checking PIA/Happ Split Tunneling Settings..." -ForegroundColor Yellow
    Write-Host " EXPECTED: Split Tunneling Enabled. 'C:/Program Files/FlyFrogLLC/Happ/core/xray.exe' -> Bypass VPN" -ForegroundColor Gray
    $piaSettingsPath = "C:\Program Files\Private Internet Access\data\settings.json"
    if (Test-Path $piaSettingsPath) {
        $settingsRaw = Get-Content -Raw $piaSettingsPath
        $settings = $settingsRaw | ConvertFrom-Json
        $xrayRule = $settings.splitTunnelRules | Where-Object { $_.mode -eq 'exclude' -and ($_.path -replace '\\','/') -eq 'C:/Program Files/FlyFrogLLC/Happ/core/xray.exe' }
        if (-not $settings.splitTunnelEnabled -or -not $xrayRule) {
            Write-Host " WARNING: PIA Split Tunneling for Happ is NOT correctly configured!" -ForegroundColor Red
            $fix = Read-Host " Do you want to Auto-Fix it? (Y/N)"
            if ($fix -match 'Y') {
                $bakPath = "$piaSettingsPath.bak_$(Get-Date -f 'yyyyMMdd_HHmmss')"
                Copy-Item $piaSettingsPath $bakPath -Force
                Write-Host " Backed up PIA settings to $bakPath" -ForegroundColor Green
                
                $settings.splitTunnelEnabled = $true
                if (-not $xrayRule) {
                    $newRule = @{
                        id = [guid]::NewGuid().ToString()
                        mode = "exclude"
                        path = "C:\Program Files\FlyFrogLLC\Happ\core\xray.exe"
                        type = "app"
                    }
                    $settings.splitTunnelRules += $newRule
                }
                $settings | ConvertTo-Json -Depth 10 | Set-Content $piaSettingsPath
                Write-Host " PIA settings fixed. Please restart PIA." -ForegroundColor Green
            }
        } else {
            Write-Host " PIA Split Tunneling for Happ is configured correctly." -ForegroundColor Green
        }
    } else {
        Write-Host " PIA settings.json not found." -ForegroundColor Red
    }

    # 4. Worker Paths and Child Scripts Correctness
    Write-Host "`n[4] Checking Workers Paths and Child Scripts..." -ForegroundColor Yellow
    1..4 | ForEach-Object {
        $wPath = Join-Path $RootDir "Profiles\Worker_$_"
        if (-not (Test-Path $wPath)) {
            New-Item -Path $wPath -ItemType Directory -Force | Out-Null
            Write-Host " Created missing Worker $_ folder." -ForegroundColor Yellow
        } else {
            Write-Host " Worker $_ folder exists." -ForegroundColor Green
        }
        $childScript = Join-Path $wPath "Start-Worker.ps1"
        if (Test-Path $childScript) {
            $content = Get-Content $childScript -Raw
            if ($content -match "(?i)Stop-Process\s+-Name\s+Antigravity") {
                Write-Host " WARNING: Found dangerous 'kill process' in Worker $_ script! Fixing..." -ForegroundColor Red
                $content = $content -replace "(?i)Stop-Process\s+-Name\s+Antigravity.*", "# [Removed dangerous Stop-Process]"
                $content | Set-Content $childScript
                Write-Host " Fixed script: $childScript" -ForegroundColor Green
            } else {
                Write-Host " Script $childScript is safe (no blind kill process)." -ForegroundColor Green
            }
        } else {
            Write-Host " WARNING: $childScript is missing!" -ForegroundColor Red
        }
    }

    # 5. Junction link verification
    Write-Host "`n[5] Checking Junction/Hardlink..." -ForegroundColor Yellow
    $TargetGemini = "C:\GIT\AGY\.gemini"
    $CommonGemini = "$RootDir\Common\.gemini"
    
    if (Test-Path $TargetGemini) {
        Write-Host " Target path $TargetGemini exists." -ForegroundColor Green
        
        $item = Get-Item $CommonGemini -ErrorAction SilentlyContinue
        if ($item -and $item.LinkType -eq 'Junction') {
            Write-Host " Junction $CommonGemini -> $($item.Target) is CORRECT." -ForegroundColor Green
        } else {
            Write-Host " WARNING: $CommonGemini is NOT a junction! You should run Setup-Junction.ps1." -ForegroundColor Red
        }
    } else {
        Write-Host " WARNING: Target path $TargetGemini is MISSING!" -ForegroundColor Red
    }

    Write-Host "`nDoctor checks complete!" -ForegroundColor Cyan
    Read-Host "Press Enter to continue..."
}

function Arrange-Windows {
    $SPI_GETWORKAREA = 48
    $rect = New-Object WinAPI+RECT
    [WinAPI]::SystemParametersInfo($SPI_GETWORKAREA, 0, [ref]$rect, 0) | Out-Null
    
    $w = $rect.Right - $rect.Left
    $h = $rect.Bottom - $rect.Top
    $halfW = [math]::Floor($w / 2)
    $halfH = [math]::Floor($h / 2)

    $wmiProcs = Get-CimInstance Win32_Process -Filter "Name = 'antigravity.exe'" -ErrorAction SilentlyContinue
    $pids = @()
    foreach ($p in $wmiProcs) {
        if ($p.CommandLine -match '--user-data-dir=.*Worker_') {
            $pids += [uint]$p.ProcessId
        }
    }

    $Script:agWindows = @()
    if ($pids.Count -gt 0) {
        $hwnds = [WinAPI]::GetWindowsForPids([uint[]]$pids)
        foreach ($hWnd in $hwnds) {
            $sb = New-Object System.Text.StringBuilder 256
            [WinAPI]::GetWindowText($hWnd, $sb, 256) | Out-Null
            $title = $sb.ToString()
            if ($title.Trim() -ne "") {
                $Script:agWindows += [PSCustomObject]@{ HWND = $hWnd; Title = $title }
            }
        }
    }

    $existingMax = 0
    foreach ($win in $Script:agWindows) {
        if ($win.Title -match "^\((\d+)\)") {
            $num = [int]$matches[1]
            if ($num -gt $existingMax) { $existingMax = $num }
        }
    }

    foreach ($win in $Script:agWindows) {
        $hWnd = $win.HWND
        $title = $win.Title
        $num = 0
        if ($title -match "^\((\d+)\)") {
            $num = [int]$matches[1]
        } else {
            $existingMax++
            $num = $existingMax
            $newTitle = "($num) $title"
            [WinAPI]::SetWindowText($hWnd, $newTitle) | Out-Null
        }
        
        $x = $rect.Left
        $y = $rect.Top
        if ($num -eq 2) { $x += $halfW }
        elseif ($num -eq 3) { $y += $halfH }
        elseif ($num -eq 4) { $x += $halfW; $y += $halfH }
        elseif ($num -gt 4) {
            $x += 50 * ($num - 4)
            $y += 50 * ($num - 4)
        }
        
        [WinAPI]::MoveWindow($hWnd, $x, $y, $halfW, $halfH, $true) | Out-Null
    }
}

function Start-Workers($Count) {
    Write-StartLog "Starting $Count workers..."
    
    $startFg = [WinAPI]::GetForegroundWindow()
    $baseWorkerCount = Get-RunningWorkersCount
    
    for ($i = 1; $i -le $Count; $i++) {
        $wNum = $baseWorkerCount + $i
        $scriptPath = Join-Path $RootDir "Profiles\Worker_$wNum\Start-Worker.ps1"
        if (Test-Path $scriptPath) {
            Write-StartLog "Launching Worker $wNum -> $scriptPath"
            Start-Process powershell.exe "-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
        } else {
            Write-StartLog "WARNING: Worker $wNum script not found at $scriptPath"
        }
    }
    
    # Wait for windows to appear and arrange
    Write-StartLog "Waiting for windows to spawn before arranging..."
    $timeout = 30
    while ($timeout -gt 0) {
        Start-Sleep -Seconds 1
        $currentFg = [WinAPI]::GetForegroundWindow()
        if ($currentFg -ne $startFg -and $currentFg -ne 0) {
            Write-StartLog "Focus lost to a new window! Terminal focus ended."
            break
        }
        $timeout--
    }
    
    Start-Sleep -Seconds 3
    Arrange-Windows
    Write-StartLog "Windows arranged and titles updated."
}

function Show-Menu {
    Clear-Host
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host "         ANTIGRAVITY MULTI-WORKER CONTROLLER           " -ForegroundColor Yellow
    Write-Host "=======================================================" -ForegroundColor Cyan
    
    $runningWorkers = Get-RunningWorkersCount
    Write-Host " Running AG Worker Instances: $runningWorkers" -ForegroundColor Green
    
    $isPortUp = [bool](Get-NetTCPConnection -LocalPort 8045 -State Listen -ErrorAction SilentlyContinue)
    if ($isPortUp) { Write-Host " AG Manager (Port 8045): RUNNING" -ForegroundColor Green }
    else { Write-Host " AG Manager (Port 8045): STOPPED" -ForegroundColor Red }
    
    Write-Host "=======================================================" -ForegroundColor Cyan
    
    if ($runningWorkers -lt 4) {
        Write-Host " [1] Start +1 Worker"
        Write-Host " [M] Start Max Workers (Fill to 4)"
    }
    Write-Host " [A] Start All 4 (Force)"
    Write-Host " [R] Restart AG Manager"
    Write-Host " [D] Diagnostic Mode"
    Write-Host " [DOC] Doctor Mode (Fix settings/shortcuts)"
    Write-Host " [U] Update Standalone App (Sync with Main)"
    Write-Host " [0] Exit"
    Write-Host "=======================================================" -ForegroundColor Cyan
}

# Main Loop
Check-Manager

while ($true) {
    Show-Menu
    $choice = Read-Host "Select action"
    switch ($choice.ToUpper()) {
        '1' { 
            Start-Workers 1 
            Read-Host "Press Enter to return..."
        }
        'M' { 
            $runningWorkers = Get-RunningWorkersCount
            $toStart = 4 - $runningWorkers
            if ($toStart -gt 0) { Start-Workers $toStart }
            Read-Host "Press Enter to return..."
        }
        'A' {
            Start-Workers 4
            Read-Host "Press Enter to return..."
        }
        'R' {
            Write-StartLog "Restarting AG Manager safely..."
            # Stop safely: kill process named antigravity-tools instead of Antigravity
            $mgrs = Get-Process antigravity-tools -ErrorAction SilentlyContinue
            if ($mgrs) {
                $mgrs | Stop-Process -Force -ErrorAction SilentlyContinue
                Write-StartLog "Stopped antigravity-tools process."
            } else {
                Write-StartLog "antigravity-tools process not found."
            }
            Start-Sleep -Seconds 1
            Check-Manager
            Read-Host "Press Enter to return..."
        }
        'D' { Run-Diagnostic }
        'DOC' { Run-Doctor }
        'U' { Sync-StandaloneApp }
        '0' { exit }
    }
}.CommandLine -match '--user-data-dir=.*Worker_' } | Stop-Process -Force -ErrorAction SilentlyContinue
        
        Start-Sleep -Seconds 2
        Robocopy $source $target /MIR /R:1 /W:1 | Out-Null
        Write-Host "Update completed successfully! Standalone is now matching main version." -ForegroundColor Green
    } else {
        Write-Host "Main installation not found at $source." -ForegroundColor Red
    }
    Read-Host "Press Enter to continue..."
}

function Arrange-Windows {
    $SPI_GETWORKAREA = 48
    $rect = New-Object WinAPI+RECT
    [WinAPI]::SystemParametersInfo($SPI_GETWORKAREA, 0, [ref]$rect, 0) | Out-Null
    
    $w = $rect.Right - $rect.Left
    $h = $rect.Bottom - $rect.Top
    $halfW = [math]::Floor($w / 2)
    $halfH = [math]::Floor($h / 2)

    $wmiProcs = Get-CimInstance Win32_Process -Filter "Name = 'antigravity.exe'" -ErrorAction SilentlyContinue
    $pids = @()
    foreach ($p in $wmiProcs) {
        if ($p.CommandLine -match '--user-data-dir=.*Worker_') {
            $pids += [uint]$p.ProcessId
        }
    }

    $Script:agWindows = @()
    if ($pids.Count -gt 0) {
        $hwnds = [WinAPI]::GetWindowsForPids([uint[]]$pids)
        foreach ($hWnd in $hwnds) {
            $sb = New-Object System.Text.StringBuilder 256
            [WinAPI]::GetWindowText($hWnd, $sb, 256) | Out-Null
            $title = $sb.ToString()
            if ($title.Trim() -ne "") {
                $Script:agWindows += [PSCustomObject]@{ HWND = $hWnd; Title = $title }
            }
        }
    }

    $existingMax = 0
    foreach ($win in $Script:agWindows) {
        if ($win.Title -match "^\((\d+)\)") {
            $num = [int]$matches[1]
            if ($num -gt $existingMax) { $existingMax = $num }
        }
    }

    foreach ($win in $Script:agWindows) {
        $hWnd = $win.HWND
        $title = $win.Title
        $num = 0
        if ($title -match "^\((\d+)\)") {
            $num = [int]$matches[1]
        } else {
            $existingMax++
            $num = $existingMax
            $newTitle = "($num) $title"
            [WinAPI]::SetWindowText($hWnd, $newTitle) | Out-Null
        }
        
        $x = $rect.Left
        $y = $rect.Top
        if ($num -eq 2) { $x += $halfW }
        elseif ($num -eq 3) { $y += $halfH }
        elseif ($num -eq 4) { $x += $halfW; $y += $halfH }
        elseif ($num -gt 4) {
            $x += 50 * ($num - 4)
            $y += 50 * ($num - 4)
        }
        
        [WinAPI]::MoveWindow($hWnd, $x, $y, $halfW, $halfH, $true) | Out-Null
    }
}

function Start-Workers($Count) {
    Write-StartLog "Starting $Count workers..."
    
    $startFg = [WinAPI]::GetForegroundWindow()
    $baseWorkerCount = Get-RunningWorkersCount
    
    for ($i = 1; $i -le $Count; $i++) {
        $wNum = $baseWorkerCount + $i
        $scriptPath = Join-Path $RootDir "Profiles\Worker_$wNum\Start-Worker.ps1"
        if (Test-Path $scriptPath) {
            Write-StartLog "Launching Worker $wNum -> $scriptPath"
            Start-Process powershell.exe "-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
        } else {
            Write-StartLog "WARNING: Worker $wNum script not found at $scriptPath"
        }
    }
    
    # Wait for windows to appear and arrange
    Write-StartLog "Waiting for windows to spawn before arranging..."
    $timeout = 30
    while ($timeout -gt 0) {
        Start-Sleep -Seconds 1
        $currentFg = [WinAPI]::GetForegroundWindow()
        if ($currentFg -ne $startFg -and $currentFg -ne 0) {
            Write-StartLog "Focus lost to a new window! Terminal focus ended."
            break
        }
        $timeout--
    }
    
    Start-Sleep -Seconds 3
    Arrange-Windows
    Write-StartLog "Windows arranged and titles updated."
}

function Show-Menu {
    Clear-Host
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host "         ANTIGRAVITY MULTI-WORKER CONTROLLER           " -ForegroundColor Yellow
    Write-Host "=======================================================" -ForegroundColor Cyan
    
    $runningWorkers = Get-RunningWorkersCount
    Write-Host " Running AG Worker Instances: $runningWorkers" -ForegroundColor Green
    
    $isPortUp = [bool](Get-NetTCPConnection -LocalPort 8045 -State Listen -ErrorAction SilentlyContinue)
    if ($isPortUp) { Write-Host " AG Manager (Port 8045): RUNNING" -ForegroundColor Green }
    else { Write-Host " AG Manager (Port 8045): STOPPED" -ForegroundColor Red }
    
    Write-Host "=======================================================" -ForegroundColor Cyan
    
    if ($runningWorkers -lt 4) {
        Write-Host " [1] Start +1 Worker"
        Write-Host " [M] Start Max Workers (Fill to 4)"
    }
    Write-Host " [A] Start All 4 (Force)"
    Write-Host " [R] Restart AG Manager"
    Write-Host " [D] Diagnostic Mode"
    Write-Host " [DOC] Doctor Mode (Fix settings/shortcuts)"
    Write-Host " [U] Update Standalone App (Sync with Main)"
    Write-Host " [0] Exit"
    Write-Host "=======================================================" -ForegroundColor Cyan
}

# Main Loop
Check-Manager

while ($true) {
    Show-Menu
    $choice = Read-Host "Select action"
    switch ($choice.ToUpper()) {
        '1' { 
            Start-Workers 1 
            Read-Host "Press Enter to return..."
        }
        'M' { 
            $runningWorkers = Get-RunningWorkersCount
            $toStart = 4 - $runningWorkers
            if ($toStart -gt 0) { Start-Workers $toStart }
            Read-Host "Press Enter to return..."
        }
        'A' {
            Start-Workers 4
            Read-Host "Press Enter to return..."
        }
        'R' {
            Write-StartLog "Restarting AG Manager safely..."
            # Stop safely: kill process named antigravity-tools instead of Antigravity
            $mgrs = Get-Process antigravity-tools -ErrorAction SilentlyContinue
            if ($mgrs) {
                $mgrs | Stop-Process -Force -ErrorAction SilentlyContinue
                Write-StartLog "Stopped antigravity-tools process."
            } else {
                Write-StartLog "antigravity-tools process not found."
            }
            Start-Sleep -Seconds 1
            Check-Manager
            Read-Host "Press Enter to return..."
        }
        'D' { Run-Diagnostic }
        'DOC' { Run-Doctor }
        'U' { Sync-StandaloneApp }
        '0' { exit }
    }
}
