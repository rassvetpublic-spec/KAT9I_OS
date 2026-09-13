param(
    [string]$Root = 'C:\Antigravity'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$SourceRoot = Split-Path -Parent $PSCommandPath
$SourceSystem = Join-Path $SourceRoot '_System'
$TargetSystem = Join-Path $Root '_System'
$Stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$BootstrapBackup = Join-Path (Join-Path $Root 'Backups\Bootstrap') $Stamp

function Get-Sha256([string]$Path) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $stream = [IO.File]::OpenRead($Path)
        try { $bytes = $sha.ComputeHash($stream) } finally { $stream.Dispose() }
    } finally { $sha.Dispose() }
    ([BitConverter]::ToString($bytes)).Replace('-','').ToLowerInvariant()
}

function Copy-FileVerified([string]$Source,[string]$Destination) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    if (-not (Test-Path -LiteralPath $Destination -PathType Leaf)) { throw "Copy failed: $Destination" }
    if ((Get-Sha256 $Source) -ne (Get-Sha256 $Destination)) { throw "Copy SHA256 verification failed: $Destination" }
}

New-Item -ItemType Directory -Force -Path $Root,$TargetSystem,$BootstrapBackup | Out-Null

foreach ($name in @('ANTIGRAVITY.cmd')) {
    $old = Join-Path $Root $name
    if (Test-Path -LiteralPath $old -PathType Leaf) { Copy-FileVerified $old (Join-Path $BootstrapBackup $name) }
}
foreach ($name in @('Antigravity-Control.ps1','Patch-Antigravity.ps1','patch-signatures.json')) {
    $old = Join-Path $TargetSystem $name
    if (Test-Path -LiteralPath $old -PathType Leaf) { Copy-FileVerified $old (Join-Path $BootstrapBackup $name) }
}

Copy-FileVerified (Join-Path $SourceRoot 'ANTIGRAVITY.cmd') (Join-Path $Root 'ANTIGRAVITY.cmd')
Copy-FileVerified (Join-Path $SourceSystem 'Antigravity-Control.ps1') (Join-Path $TargetSystem 'Antigravity-Control.ps1')
Copy-FileVerified (Join-Path $SourceSystem 'Patch-Antigravity.ps1') (Join-Path $TargetSystem 'Patch-Antigravity.ps1')
Copy-FileVerified (Join-Path $SourceSystem 'patch-signatures.json') (Join-Path $TargetSystem 'patch-signatures.json')

Write-Host "Installed bootstrap to $Root"
Write-Host "Single entry point: $(Join-Path $Root 'ANTIGRAVITY.cmd')"
Write-Host "Bootstrap backup: $BootstrapBackup"
Write-Host 'Running read-only status...'
$controller = Join-Path $TargetSystem 'Antigravity-Control.ps1'
$hostExe = if (Get-Command pwsh.exe -ErrorAction SilentlyContinue) { (Get-Command pwsh.exe).Source } else { (Get-Command powershell.exe).Source }
& $hostExe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $controller status -Root $Root
$statusRc = [int]$LASTEXITCODE
exit $statusRc
