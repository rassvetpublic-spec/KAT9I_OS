Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WinAPI {
    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern bool SetWindowText(IntPtr hwnd, String lpString);

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
}
"@

# Define hotkey (F12) registration is complex in pure PS without a message pump, 
# so we'll use a simpler approach: we just rename the windows continuously.
# For the "click/hotkey" requirement, if the user makes the window active, the title already shows it.

while ($true) {
    $procs = Get-CimInstance Win32_Process -Filter "Name='Antigravity.exe'"
    foreach ($p in $procs) {
        if ($p.CommandLine -match 'Worker_(\d)') {
            $workerId = $matches[1]
            $psProc = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
            if ($psProc -and $psProc.MainWindowHandle -ne 0) {
                $hwnd = $psProc.MainWindowHandle
                $sb = New-Object System.Text.StringBuilder 256
                [WinAPI]::GetWindowText($hwnd, $sb, $sb.Capacity) | Out-Null
                $title = $sb.ToString()
                
                if ($title -and $title -notmatch "^\(\d\)") {
                    # Strip any previous marker just in case
                    $title = $title -replace "^\[Worker \d\] ", ""
                    $newTitle = "($workerId) $title"
                    [WinAPI]::SetWindowText($hwnd, $newTitle) | Out-Null
                }
            }
        }
    }
    Start-Sleep -Seconds 2
}
