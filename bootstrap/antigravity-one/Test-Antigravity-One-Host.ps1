param(
    [string]$Root = 'C:\Antigravity',
    [ValidateSet('ReadOnly','Install','Repair')]
    [string]$Mode = 'ReadOnly',
    [switch]$AllowMutation,
    [string]$EvidencePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Normalize-Path([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    foreach ($pair in @(
        @($env:LOCALAPPDATA,'%LOCALAPPDATA%'),
        @($env:APPDATA,'%APPDATA%'),
        @($env:USERPROFILE,'%USERPROFILE%')
    )) {
        if ($pair[0] -and $full.StartsWith([string]$pair[0],[StringComparison]::OrdinalIgnoreCase)) {
            return ([string]$pair[1]) + $full.Substring(([string]$pair[0]).Length)
        }
    }
    return $full
}

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $stream = [IO.File]::OpenRead($Path)
        try { $bytes = $sha.ComputeHash($stream) } finally { $stream.Dispose() }
    } finally { $sha.Dispose() }
    return ([BitConverter]::ToString($bytes)).Replace('-','').ToLowerInvariant()
}

function Get-ProtectedSnapshot {
    $items = [ordered]@{}
    foreach ($relative in @('Standalone\Profile','_Manager\Data','_Manager\State')) {
        $path = Join-Path $Root $relative
        $item = Get-Item -LiteralPath $path -ErrorAction SilentlyContinue
        $items[$relative] = [ordered]@{
            exists = [bool]$item
            last_write_utc = if ($item) { $item.LastWriteTimeUtc.ToString('o') } else { $null }
        }
    }
    $patchState = Join-Path $Root '_System\patch-state.json'
    $items['patch-state.json'] = [ordered]@{
        exists = Test-Path -LiteralPath $patchState -PathType Leaf
        sha256 = Get-Sha256 $patchState
    }
    return $items
}

function Invoke-Entry([string]$Command) {
    $entry = Join-Path $Root 'ANTIGRAVITY.cmd'
    if (-not (Test-Path -LiteralPath $entry -PathType Leaf)) {
        throw "Antigravity ONE entry point missing: $(Normalize-Path $entry)"
    }
    $line = '""{0}" {1}"' -f $entry,$Command
    & $env:ComSpec /d /c $line
    return [int]$LASTEXITCODE
}

if ($Mode -ne 'ReadOnly' -and -not $AllowMutation) {
    throw 'Mutation mode requires explicit -AllowMutation.'
}

if (-not $EvidencePath) {
    $evidenceDir = Join-Path $Root '_System\HostEvidence'
    New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
    $EvidencePath = Join-Path $evidenceDir ('host-smoke_{0}.json' -f (Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'))
}

$before = Get-ProtectedSnapshot
$results = New-Object System.Collections.Generic.List[object]
$status = 'BLOCKED'
$exitCode = 1

try {
    $statusRc = Invoke-Entry 'status'
    $results.Add([ordered]@{command='status';exit_code=$statusRc})

    $dryRunRc = Invoke-Entry 'dryrun'
    $results.Add([ordered]@{command='dryrun';exit_code=$dryRunRc})

    if ($statusRc -ne 0 -or $dryRunRc -ne 0) {
        $status = 'BLOCKED_INCOMPATIBLE_OR_UNDISCOVERED'
        $exitCode = if ($statusRc -ne 0) { $statusRc } else { $dryRunRc }
    } else {
        if ($Mode -eq 'Install') {
            $rc = Invoke-Entry 'install'
            $results.Add([ordered]@{command='install';exit_code=$rc})
            if ($rc -ne 0) { throw "Install host smoke failed with exit code $rc" }
        } elseif ($Mode -eq 'Repair') {
            $rc = Invoke-Entry 'repair'
            $results.Add([ordered]@{command='repair';exit_code=$rc})
            if ($rc -ne 0) { throw "Repair host smoke failed with exit code $rc" }
        }
        $status = 'HOST_SMOKE_PASS'
        $exitCode = 0
    }
} catch {
    $results.Add([ordered]@{command='harness';exit_code=1;error=$_.Exception.Message})
    $status = 'HOST_SMOKE_FAILED'
    $exitCode = 1
}

$after = Get-ProtectedSnapshot
if ($Mode -eq 'ReadOnly') {
    $beforeJson = $before | ConvertTo-Json -Depth 10 -Compress
    $afterJson = $after | ConvertTo-Json -Depth 10 -Compress
    if ($beforeJson -ne $afterJson) {
        $status = 'READ_ONLY_MUTATION_DETECTED'
        $exitCode = 1
    }
}

$evidence = [ordered]@{
    schema = 1
    generated_at = (Get-Date).ToUniversalTime().ToString('o')
    root = Normalize-Path $Root
    mode = $Mode
    mutation_authorized = [bool]$AllowMutation
    status = $status
    commands = @($results)
    protected_state_before = $before
    protected_state_after = $after
}

$dir = Split-Path -Parent $EvidencePath
if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
[IO.File]::WriteAllText($EvidencePath,($evidence | ConvertTo-Json -Depth 20) + "`r`n",[Text.UTF8Encoding]::new($false))
Write-Host ("{0} evidence={1}" -f $status,(Normalize-Path $EvidencePath))
exit $exitCode
