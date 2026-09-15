Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinAPI {
    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
    
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea

$procs = Get-CimInstance Win32_Process -Filter "Name='Antigravity.exe'" | Where-Object { $_.CommandLine -match 'Worker_(\d+)' }
$count = $procs.Count
if ($count -eq 0) { exit }

# Calculate optimal grid (cols x rows)
$cols = [math]::Ceiling([math]::Sqrt($count))
$rows = [math]::Ceiling($count / $cols)

$w = [math]::Floor($screen.Width / $cols)
$h = [math]::Floor($screen.Height / $rows)

# Windows 10/11 invisible window borders are typically 7 pixels on left, right, and bottom.
$borderOffset = 7

# Sort processes by Worker ID so they are arranged in order
$sortedProcs = $procs | Sort-Object { [int]($_.CommandLine -replace '.*Worker_(\d+).*', '$1') }

$index = 0
foreach ($p in $sortedProcs) {
    $psProc = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
    if ($psProc -and $psProc.MainWindowHandle -ne 0) {
        $col = $index % $cols
        $row = [math]::Floor($index / $cols)
        
        $baseX = $screen.Left + ($col * $w)
        $baseY = $screen.Top + ($row * $h)
        
        [WinAPI]::ShowWindow($psProc.MainWindowHandle, 1) # SW_SHOWNORMAL
        
        # Compensate for invisible borders to make them visually snap
        $adjustedX = $baseX - $borderOffset
        $adjustedY = $baseY # Top usually has no invisible border
        $adjustedW = $w + ($borderOffset * 2)
        $adjustedH = $h + $borderOffset
        
        [WinAPI]::MoveWindow($psProc.MainWindowHandle, $adjustedX, $adjustedY, $adjustedW, $adjustedH, $true)
        $index++
    }
}
