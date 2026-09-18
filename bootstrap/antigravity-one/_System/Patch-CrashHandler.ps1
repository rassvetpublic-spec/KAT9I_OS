$extractDir = "C:\Antigravity\Standalone\App\resources\app-extracted"
$asarPath = "C:\Antigravity\Standalone\App\resources\app.asar"

if (-not (Test-Path $extractDir)) {
    Write-Host "Extracting ASAR..."
    npx asar extract $asarPath $extractDir
}

$mainJs = "$extractDir\dist\main.js"
$content = Get-Content $mainJs -Raw

if ($content -notmatch '\[CRASH HANDLER\]') {
    Write-Host "Patching main.js..."
    $patch = "
electron_1.app.on('browser-window-created', (event, win) => {
    win.webContents.on('render-process-gone', (e, details) => {
        console.error('[CRASH HANDLER] Renderer gone:', details);
        setTimeout(() => { if (!win.isDestroyed()) win.reload(); }, 1000);
    });
    win.webContents.on('unresponsive', () => {
        console.error('[CRASH HANDLER] Window unresponsive');
        if (!win.isDestroyed()) win.reload();
    });
    win.webContents.on('did-fail-load', (e, code, desc, url) => {
        if (url.includes('127.0.0.1')) {
            console.error('[CRASH HANDLER] Failed to load URL, retrying...', desc);
            setTimeout(() => { if (!win.isDestroyed()) win.reload(); }, 1000);
        }
    });
    win.webContents.on('before-input-event', (event, input) => {
        if (input.control && input.key.toLowerCase() === 'r') {
            win.reload();
            event.preventDefault();
        }
        if (input.key === 'F5') {
            win.reload();
            event.preventDefault();
        }
    });
});
"
    $content = $content -replace "electron_1\.app\.whenReady\(\)\.then", "$patch`nelectron_1.app.whenReady().then"
    $content | Set-Content $mainJs -Encoding UTF8
    
    Write-Host "Repacking ASAR..."
    npx asar pack $extractDir $asarPath
} else {
    Write-Host "Already patched."
}
