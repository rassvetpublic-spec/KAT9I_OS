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
$PatchStatePath = Join-Path $SystemDir 'patch-state.json'
$ManifestPath = Join-Path $SystemDir 'patch-signatures.json'
$ReceiptDir = Join-Path $SystemDir 'Receipts'
$StateBackupRoot = Join-Path $Root 'Backups\State'
$FallbackBackupRoot = Join-Path $Root 'Backups\Fallback'
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

function Add-Candidate([System.Collections.Generic.List[string]]$List,[string]$Base,[string]$Relative) {
    if (-not $Base) { return }
    $p = Join-Path $Base $Relative
    if (Test-Path -LiteralPath $p -PathType Leaf) { $List.Add([IO.Path]::GetFullPath($p)) }
}

function Get-KnownTargets {
    $items = New-Object System.Collections.Generic.List[string]
    Add-Candidate $items $Root 'Standalone\App\resources\bin\language_server.exe'
    Add-Candidate $items $env:LOCALAPPDATA 'Programs\antigravity\resources\bin\language_server.exe'
    Add-Candidate $items $env:ProgramFiles 'Antigravity\resources\bin\language_server.exe'
    Add-Candidate $items ${env:ProgramFiles(x86)} 'Antigravity\resources\bin\language_server.exe'
    return @($items | Sort-Object -Unique)
}

function Test-ConsumerRunning {
    return [bool](Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -in @('Antigravity','language_server') })
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
    foreach ($item in @(
        @((Join-Path $Root 'Standalone\Profile'), (Join-Path $dest 'Standalone_Profile')),
        @((Join-Path $Root '_Manager\Data'), (Join-Path $dest 'Manager_Data')),
        @((Join-Path $Root '_Manager\State'), (Join-Path $dest 'Manager_State'))
    )) { Copy-TreeVerified $item[0] $item[1] }
    [IO.File]::WriteAllText((Join-Path $dest 'backup.json'),([ordered]@{schema=1;time=(Get-Date).ToString('o');reason=$Reason} | ConvertTo-Json) + "`r`n",[Text.UTF8Encoding]::new($false))
    Write-Host "Verified state backup: $dest"
    return $dest
}

function Invoke-NativePatch([string]$Mode) {
    if (-not (Test-Path -LiteralPath $PatchScript)) { throw "Patch engine missing: $PatchScript" }
    & $PatchScript -Mode $Mode -Root $Root -AllowIssueWrite:$AllowIssueWrite
    return $LASTEXITCODE
}

function Get-LatestReceipt {
    Get-ChildItem -LiteralPath $ReceiptDir -Filter 'patch_*.json' -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
}

function New-FallbackBinarySnapshot {
    if (Test-ConsumerRunning) { throw 'Fallback blocked: Antigravity/language_server is running.' }
    $targets = @(Get-KnownTargets)
    if (-not $targets.Count) { throw 'Fallback blocked: no language_server.exe targets found.' }
    $stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
    $dest = Join-Path $FallbackBackupRoot $stamp
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $records = New-Object System.Collections.Generic.List[object]
    $i = 0
    foreach ($target in $targets) {
        $hash = Get-Sha256 $target
        $backup = Join-Path $dest ("language_server_{0}.exe" -f $i)
        Copy-Item -LiteralPath $target -Destination $backup -Force
        if ((Get-Sha256 $backup) -ne $hash) { throw "Fallback backup verification failed: $target" }
        $records.Add([ordered]@{target=$target;public_target=(Normalize-Path $target);source_sha256=$hash;backup=$backup})
        $i++
    }
    $snapshot = [ordered]@{schema=1;created_at=(Get-Date).ToString('o');records=@($records)}
    [IO.File]::WriteAllText((Join-Path $dest 'snapshot.json'),($snapshot | ConvertTo-Json -Depth 10) + "`r`n",[Text.UTF8Encoding]::new($false))
    return [pscustomobject]@{Path=$dest;Snapshot=$snapshot}
}

function Restore-FallbackSnapshot($Snapshot) {
    $errors = New-Object System.Collections.Generic.List[string]
    foreach ($r in $Snapshot.records) {
        try {
            Copy-Item -LiteralPath $r.backup -Destination $r.target -Force
            if ((Get-Sha256 $r.target) -ne [string]$r.source_sha256) { throw "restore hash mismatch: $($r.public_target)" }
        } catch { $errors.Add($_.Exception.Message) }
    }
    if ($errors.Count) { throw ('Fallback rollback failed: ' + ($errors -join '; ')) }
}

function Register-VerifiedFallback($Snapshot) {
    [void](Invoke-NativePatch 'status')
    $receiptFile = Get-LatestReceipt
    if (-not $receiptFile) { throw 'Fallback verification receipt missing.' }
    $receipt = Get-Content -LiteralPath $receiptFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    $byTarget = @{}
    foreach ($t in @($receipt.targets)) { $byTarget[[string]$t.target] = $t }

    $manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $records = @()
    if (Test-Path -LiteralPath $PatchStatePath) {
        $old = Get-Content -LiteralPath $PatchStatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $records = @($old.records)
    }

    try {
        foreach ($r in $Snapshot.records) {
            $current = Get-Sha256 $r.target
            if ($current -eq [string]$r.source_sha256) { throw "Fallback did not modify target: $($r.public_target)" }
            $evidence = $byTarget[[string]$r.public_target]
            if (-not $evidence -or [string]$evidence.state -ne 'PATCHED') { throw "Fallback result is not a recognized patched signature: $($r.public_target)" }
            $sigs = @($manifest.signatures | Where-Object { [string]$_.architecture -eq [string]$evidence.architecture })
            if ($sigs.Count -ne 1) { throw "Fallback signature mapping is ambiguous: $($r.public_target)" }
            $records = @($records | Where-Object { [string]$_.target -ne [string]$r.public_target })
            $records += [ordered]@{
                target=[string]$r.public_target;version=[string]$evidence.version;architecture=[string]$evidence.architecture;
                source_sha256=[string]$r.source_sha256;patched_sha256=$current;signature_id=[string]$sigs[0].id;
                backup=[string]$r.backup;authority='explicit-external-fallback';patched_at=(Get-Date).ToString('o')
            }
        }
        $state = [ordered]@{schema=1;records=@($records)}
        $tmp = $PatchStatePath + '.tmp'
        [IO.File]::WriteAllText($tmp,($state | ConvertTo-Json -Depth 20) + "`r`n",[Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $tmp -Destination $PatchStatePath -Force
        $rc = Invoke-NativePatch 'status'
        if ($rc -ne 0) { throw 'Registered fallback did not pass native status verification.' }
    } catch {
        Restore-FallbackSnapshot $Snapshot
        throw
    }
}

function Invoke-ExplicitFallback {
    Write-Host 'EXPLICIT FALLBACK: external Open AG Patcher will be used only for this request.'
    $stateBackup = New-StateBackup 'before_fallback'
    $binarySnapshot = New-FallbackBinarySnapshot
    $api = 'https://api.github.com/repos/AvenCores/open-antigravity-patcher/releases/latest'
    $headers = @{ 'User-Agent'='KAT9I-Antigravity-One' }
    $release = Invoke-RestMethod -Uri $api -Headers $headers
    $arch = if ($env:PROCESSOR_ARCHITEW6432 -match 'ARM64' -or $env:PROCESSOR_ARCHITECTURE -match 'ARM64') {'ARM64'} else {'x64'}
    $asset = @($release.assets | Where-Object { $_.name -match ("(?i)Windows[_-]" + [regex]::Escape($arch) + "\.exe$") }) | Select-Object -First 1
    if (-not $asset) { throw "No matching fallback asset for $arch in $($release.tag_name)" }
    New-Item -ItemType Directory -Force -Path $FallbackDir | Out-Null
    $exe = Join-Path $FallbackDir $asset.name
    Invoke-WebRequest -Uri $asset.browser_download_url -Headers $headers -OutFile $exe
    $actual = Get-Sha256 $exe
    if ($asset.digest -match '^sha256:(.+)$') {
        $expected = $Matches[1].ToLowerInvariant()
        if ($actual -ne $expected) { throw 'Fallback patcher SHA256 mismatch' }
    }
    Write-Host "Fallback downloaded: $exe"
    Write-Host "State backup: $stateBackup"
    Write-Host "Binary snapshot: $($binarySnapshot.Path)"
    Write-Host 'Launching interactive upstream fallback. Native patch remains primary.'
    Start-Process -FilePath $exe -Wait
    Register-VerifiedFallback $binarySnapshot.Snapshot
    Write-Host 'FALLBACK_VERIFIED: external change registered only after native signature/hash verification.'
}

function Try-IssueEscalation {
    if (-not $AllowIssueWrite) { return }
    if (-not (Get-Command gh.exe -ErrorAction SilentlyContinue)) { Write-Host 'Issue escalation skipped: gh.exe unavailable.'; return }
    $latest = Get-LatestReceipt
    if (-not $latest) { return }
    $body = Get-Content -LiteralPath $latest.FullName -Raw -Encoding UTF8
    if ($body -notmatch 'PATCH_BLOCKED') { return }
    $title = '[Compatibility][Antigravity ONE] Unknown/blocked language_server build'
    $existing = & gh issue list --repo $IssueRepo --state open --search 'Unknown/blocked language_server build in:title' --json number --jq '.[0].number' 2>$null
    if ($LASTEXITCODE -eq 0 -and $existing) { Write-Host "Compatibility Issue already exists: #$existing"; return }
    $issueBody = "Compatibility receipt (sanitized):`r`n" + $body
    & gh issue create --repo $IssueRepo --title $title --body $issueBody | Out-Host
}

switch ($Command) {
    'status' { exit (Invoke-NativePatch 'status') }
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
    'fallback' { Invoke-ExplicitFallback; exit 0 }
}
