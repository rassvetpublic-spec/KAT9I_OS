param(
    [Parameter(Position=0)]
    [ValidateSet('status','install','repair','fallback')]
    [string]$Command = 'status',
    [string]$Root = 'C:\Antigravity',
    [switch]$AllowIssueWrite
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$SystemDir = Join-Path $Root '_System'
$PatchScript = Join-Path $SystemDir 'Patch-Antigravity.ps1'
$StateBackupRoot = Join-Path $Root 'Backups\State'
$FallbackDir = Join-Path $SystemDir 'Fallback'
$IssueRepo = 'rassvetpublic-spec/KAT9I_OS'

function Get-Sha256([string]$Path) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $stream = [IO.File]::OpenRead($Path)
        try { $bytes = $sha.ComputeHash($stream) } finally { $stream.Dispose() }
    } finally { $sha.Dispose() }
    ([BitConverter]::ToString($bytes)).Replace('-','').ToLowerInvariant()
}

function Copy-TreeVerified([string]$Source,[string]$Destination) {
    if (-not (Test-Path -LiteralPath $Source)) { return }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    & robocopy $Source $Destination /E /COPY:DAT /DCOPY:T /R:2 /W:1 /XJ /NFL /NDL /NJH /NJS | Out-Null
    if ($LASTEXITCODE -gt 7) { throw "Backup copy failed ($LASTEXITCODE): $Source" }
    if (-not (Test-Path -LiteralPath $Destination)) { throw "Backup destination missing: $Destination" }
}

function New-StateBackup([string]$Reason) {
    $stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
    $dest = Join-Path $StateBackupRoot ("{0}_{1}" -f $stamp,$Reason)
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $items = @(
        @((Join-Path $Root 'Standalone\Profile'), (Join-Path $dest 'Standalone_Profile')),
        @((Join-Path $Root '_Manager\Data'), (Join-Path $dest 'Manager_Data')),
        @((Join-Path $Root '_Manager\State'), (Join-Path $dest 'Manager_State'))
    )
    foreach ($item in $items) { Copy-TreeVerified $item[0] $item[1] }
    [IO.File]::WriteAllText((Join-Path $dest 'backup.json'),([ordered]@{schema=1;time=(Get-Date).ToString('o');reason=$Reason} | ConvertTo-Json) + "`r`n",[Text.UTF8Encoding]::new($false))
    Write-Host "Verified state backup: $dest"
    return $dest
}

function Invoke-NativePatch([string]$Mode) {
    if (-not (Test-Path -LiteralPath $PatchScript)) { throw "Patch engine missing: $PatchScript" }
    & $PatchScript -Mode $Mode -Root $Root -AllowIssueWrite:$AllowIssueWrite
    return $LASTEXITCODE
}

function Invoke-ExplicitFallback {
    Write-Host 'EXPLICIT FALLBACK: external Open AG Patcher will be used only for this request.'
    $backup = New-StateBackup 'before_fallback'
    $api = 'https://api.github.com/repos/AvenCores/open-antigravity-patcher/releases/latest'
    $headers = @{ 'User-Agent'='KAT9I-Antigravity-One' }
    $release = Invoke-RestMethod -Uri $api -Headers $headers
    $arch = if ($env:PROCESSOR_ARCHITECTURE -match 'ARM64') {'ARM64'} else {'x64'}
    $asset = @($release.assets | Where-Object { $_.name -match ("(?i)Windows[_-]" + [regex]::Escape($arch) + "\.exe$") }) | Select-Object -First 1
    if (-not $asset) { throw "No matching fallback asset for $arch in $($release.tag_name)" }
    New-Item -ItemType Directory -Force -Path $FallbackDir | Out-Null
    $exe = Join-Path $FallbackDir $asset.name
    Invoke-WebRequest -Uri $asset.browser_download_url -Headers $headers -OutFile $exe
    $actual = Get-Sha256 $exe
    if ($asset.digest -match '^sha256:(.+)$') {
        $expected = $Matches[1].ToLowerInvariant()
        if ($actual -ne $expected) { throw "Fallback patcher SHA256 mismatch" }
    }
    Write-Host "Fallback downloaded: $exe"
    Write-Host "State backup: $backup"
    Write-Host 'Launching interactive upstream fallback. Native patch remains primary.'
    Start-Process -FilePath $exe -Wait
    $rc = Invoke-NativePatch 'status'
    if ($rc -ne 0) { throw 'Fallback finished, but native status verification is not OK. Manual review required.' }
}

function Try-IssueEscalation {
    if (-not $AllowIssueWrite) { return }
    if (-not (Get-Command gh.exe -ErrorAction SilentlyContinue)) {
        Write-Host 'Issue escalation skipped: gh.exe unavailable.'
        return
    }
    $latest = Get-ChildItem -LiteralPath (Join-Path $SystemDir 'Receipts') -Filter 'patch_*.json' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) { return }
    $body = Get-Content -LiteralPath $latest.FullName -Raw -Encoding UTF8
    if ($body -notmatch 'PATCH_BLOCKED') { return }
    $title = '[Compatibility][Antigravity ONE] Unknown/blocked language_server build'
    $existing = & gh issue list --repo $IssueRepo --state open --search 'Unknown/blocked language_server build in:title' --json number --jq '.[0].number' 2>$null
    if ($LASTEXITCODE -eq 0 -and $existing) { Write-Host "Compatibility Issue already exists: #$existing"; return }
    & gh issue create --repo $IssueRepo --title $title --body "Compatibility receipt (sanitized):`n```json`n$body`n```" | Out-Host
}

switch ($Command) {
    'status' {
        $rc = Invoke-NativePatch 'status'
        exit $rc
    }
    'install' {
        New-StateBackup 'before_install' | Out-Null
        $rc = Invoke-NativePatch 'patch'
        if ($rc -ne 0) { Try-IssueEscalation; exit $rc }
        exit 0
    }
    'repair' {
        New-StateBackup 'before_repair' | Out-Null
        $rc = Invoke-NativePatch 'patch'
        if ($rc -ne 0) { Try-IssueEscalation; exit $rc }
        exit 0
    }
    'fallback' {
        Invoke-ExplicitFallback
        exit 0
    }
}
