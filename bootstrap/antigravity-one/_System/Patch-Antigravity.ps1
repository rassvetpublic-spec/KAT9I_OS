param(
    [ValidateSet('status','patch','restore')]
    [string]$Mode = 'status',
    [string]$Root = 'C:\Antigravity',
    [switch]$AllowIssueWrite
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$SystemDir = Join-Path $Root '_System'
$ManifestPath = Join-Path $SystemDir 'patch-signatures.json'
$PatchStatePath = Join-Path $SystemDir 'patch-state.json'
$ReceiptDir = Join-Path $SystemDir 'Receipts'
$PatchBackupRoot = Join-Path $Root 'Backups\Patches'

function Get-Sha256([string]$Path) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $stream = [IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        try { $bytes = $sha.ComputeHash($stream) } finally { $stream.Dispose() }
    } finally { $sha.Dispose() }
    ([BitConverter]::ToString($bytes)).Replace('-','').ToLowerInvariant()
}

function Normalize-Path([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    $pairs = @(
        @($env:LOCALAPPDATA,'%LOCALAPPDATA%'),
        @($env:APPDATA,'%APPDATA%'),
        @($env:USERPROFILE,'%USERPROFILE%')
    )
    foreach ($pair in $pairs) {
        if ($pair[0] -and $full.StartsWith([string]$pair[0],[StringComparison]::OrdinalIgnoreCase)) {
            return ([string]$pair[1]) + $full.Substring(([string]$pair[0]).Length)
        }
    }
    return $full
}

function Normalize-Text([string]$Text) {
    if ($null -eq $Text) { return '' }
    $safe = [string]$Text
    foreach ($pair in @(
        @($env:LOCALAPPDATA,'%LOCALAPPDATA%'),
        @($env:APPDATA,'%APPDATA%'),
        @($env:USERPROFILE,'%USERPROFILE%')
    )) {
        if ($pair[0]) {
            $safe = [regex]::Replace($safe,[regex]::Escape([string]$pair[0]),[string]$pair[1],[Text.RegularExpressions.RegexOptions]::IgnoreCase)
        }
    }
    $safe = [regex]::Replace($safe,'(?i)C:\\Users\\[^\\\s"'']+','%USERPROFILE%')
    return $safe
}

function Convert-HexBytes([string]$Hex) {
    $clean = ($Hex -replace '\s','')
    if (($clean.Length % 2) -ne 0) { throw "Invalid hex length" }
    $bytes = New-Object byte[] ($clean.Length / 2)
    for ($i=0; $i -lt $bytes.Length; $i++) {
        $bytes[$i] = [Convert]::ToByte($clean.Substring($i*2,2),16)
    }
    return $bytes
}

function Get-PeArchitecture([string]$Path) {
    $fs = [IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
    try {
        $br = New-Object IO.BinaryReader($fs)
        if ($br.ReadUInt16() -ne 0x5A4D) { throw 'Not an MZ executable' }
        $fs.Position = 0x3C
        $pe = $br.ReadInt32()
        if ($pe -lt 0 -or $pe -gt ($fs.Length - 6)) { throw 'Invalid PE header offset' }
        $fs.Position = $pe
        if ($br.ReadUInt32() -ne 0x00004550) { throw 'Missing PE signature' }
        $machine = $br.ReadUInt16()
        if ($machine -eq 0x8664) { return 'x64' }
        if ($machine -eq 0xAA64) { return 'arm64' }
        return ('unknown-0x{0:X4}' -f $machine)
    } finally { $fs.Dispose() }
}

function Get-ProductVersion([string]$Target) {
    $appRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $Target))
    $exe = Join-Path $appRoot 'Antigravity.exe'
    if (Test-Path -LiteralPath $exe) {
        $raw = [Diagnostics.FileVersionInfo]::GetVersionInfo($exe).ProductVersion
        if ($raw -match '\d+\.\d+(?:\.\d+){0,2}') { return $Matches[0] }
    }
    return 'unknown'
}

function Convert-Pattern([string]$Pattern) {
    $tokens = @()
    foreach ($t in ($Pattern -split '\s+')) {
        if (-not $t) { continue }
        if ($t -eq '??') { $tokens += $null } else { $tokens += [Convert]::ToByte($t,16) }
    }
    return ,$tokens
}

function Find-PatternOffsets([byte[]]$Data,[string]$Pattern) {
    $tokens = Convert-Pattern $Pattern
    $hits = New-Object System.Collections.Generic.List[int]
    if ($tokens.Count -gt $Data.Length) { return @() }
    for ($i=0; $i -le $Data.Length-$tokens.Count; $i++) {
        $ok = $true
        for ($j=0; $j -lt $tokens.Count; $j++) {
            if ($null -ne $tokens[$j] -and $Data[$i+$j] -ne [byte]$tokens[$j]) { $ok=$false; break }
        }
        if ($ok) { $hits.Add($i) }
    }
    return @($hits)
}

function Find-UniqueAcrossPatterns([byte[]]$Data,$Patterns) {
    $set = New-Object 'System.Collections.Generic.HashSet[int]'
    foreach ($p in $Patterns) { foreach ($o in (Find-PatternOffsets $Data ([string]$p))) { [void]$set.Add([int]$o) } }
    if ($set.Count -eq 0) { return $null }
    if ($set.Count -ne 1) { throw "signature is ambiguous: offsets=$([string]::Join(',',@($set)))" }
    return [int](@($set)[0])
}

function Get-SignatureState([byte[]]$Data,$Signature) {
    $patched = Find-UniqueAcrossPatterns $Data $Signature.patched_patterns
    $original = Find-UniqueAcrossPatterns $Data $Signature.original_patterns
    if ($null -ne $patched -and $null -ne $original) { throw 'both original and patched signatures found' }
    if ($null -ne $patched) { return [pscustomobject]@{State='PATCHED';Offset=$patched} }
    if ($null -ne $original) { return [pscustomobject]@{State='ORIGINAL';Offset=$original} }
    return [pscustomobject]@{State='UNKNOWN';Offset=$null}
}

function Add-Candidate([System.Collections.Generic.List[string]]$List,[string]$Base,[string]$Relative) {
    if (-not $Base) { return }
    $p = Join-Path $Base $Relative
    if (Test-Path -LiteralPath $p -PathType Leaf) { $List.Add([IO.Path]::GetFullPath($p)) }
}

function Get-Targets {
    $candidates = New-Object System.Collections.Generic.List[string]
    Add-Candidate $candidates $Root 'Standalone\App\resources\bin\language_server.exe'
    Add-Candidate $candidates $env:LOCALAPPDATA 'Programs\antigravity\resources\bin\language_server.exe'
    Add-Candidate $candidates $env:ProgramFiles 'Antigravity\resources\bin\language_server.exe'
    Add-Candidate $candidates ${env:ProgramFiles(x86)} 'Antigravity\resources\bin\language_server.exe'
    return @($candidates | Sort-Object -Unique)
}

function Test-ConsumerRunning {
    return [bool](Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -in @('Antigravity','language_server') })
}

function Load-Manifest {
    if (-not (Test-Path -LiteralPath $ManifestPath)) { throw "Manifest missing: $ManifestPath" }
    $m = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($m.schema -ne 1) { throw 'Unsupported manifest schema' }
    return $m
}

function Load-PatchState {
    if (-not (Test-Path -LiteralPath $PatchStatePath)) { return [pscustomobject]@{schema=1;records=@()} }
    try {
        $s = Get-Content -LiteralPath $PatchStatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($s.schema -ne 1) { throw 'Unsupported patch-state schema' }
        return $s
    } catch {
        throw "Invalid patch-state: $(Normalize-Text $_.Exception.Message)"
    }
}

function Save-PatchState($State) {
    New-Item -ItemType Directory -Force -Path $SystemDir | Out-Null
    $tmp = $PatchStatePath + '.tmp'
    [IO.File]::WriteAllText($tmp,($State | ConvertTo-Json -Depth 20) + "`r`n",[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $PatchStatePath -Force
}

function Find-Compatibility($Manifest,[string]$Version,[string]$Arch,[string]$Hash) {
    @($Manifest.compatibility | Where-Object {
        ([string]$_.product_version -eq $Version) -and ([string]$_.architecture -eq $Arch) -and ([string]$_.source_sha256 -eq $Hash)
    }) | Select-Object -First 1
}

function Get-Signature($Manifest,[string]$Id) {
    @($Manifest.signatures | Where-Object { [string]$_.id -eq $Id }) | Select-Object -First 1
}

function Find-StateRecord($State,[string]$PublicTarget,[string]$Version,[string]$Arch,[string]$CurrentHash) {
    @($State.records | Where-Object {
        ([string]$_.target -eq $PublicTarget) -and ([string]$_.version -eq $Version) -and
        ([string]$_.architecture -eq $Arch) -and ([string]$_.patched_sha256 -eq $CurrentHash)
    }) | Select-Object -First 1
}

function Upsert-StateRecord($State,$Record) {
    $records = @($State.records | Where-Object { [string]$_.target -ne [string]$Record.target })
    $records += $Record
    $State.records = @($records)
}

function Write-Receipt($Payload) {
    New-Item -ItemType Directory -Force -Path $ReceiptDir | Out-Null
    $path = Join-Path $ReceiptDir ("patch_{0}.json" -f (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
    $json = $Payload | ConvertTo-Json -Depth 20
    [IO.File]::WriteAllText($path,$json + "`r`n",[Text.UTF8Encoding]::new($false))
    return $path
}

function New-VerifiedBackup([string]$Target,[string]$Version,[string]$Hash) {
    $dir = Join-Path (Join-Path $PatchBackupRoot $Version) $Hash
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $backup = Join-Path $dir 'language_server.exe'
    if (-not (Test-Path -LiteralPath $backup)) { Copy-Item -LiteralPath $Target -Destination $backup -Force }
    $bhash = Get-Sha256 $backup
    if ($bhash -ne $Hash) { throw "Backup verification failed: $(Normalize-Path $backup)" }
    return $backup
}

function Restore-Verified([string]$Target,[string]$Backup,[string]$ExpectedHash) {
    if (-not (Test-Path -LiteralPath $Backup -PathType Leaf)) { throw "Rollback backup missing: $(Normalize-Path $Backup)" }
    Copy-Item -LiteralPath $Backup -Destination $Target -Force
    if ((Get-Sha256 $Target) -ne $ExpectedHash) { throw "Rollback verification failed: $(Normalize-Path $Target)" }
}

$manifest = Load-Manifest
$patchState = Load-PatchState
$targets = @(Get-Targets)
$results = New-Object System.Collections.Generic.List[object]

if ($targets.Count -eq 0) {
    $receipt = Write-Receipt ([ordered]@{schema=1;time=(Get-Date).ToString('o');mode=$Mode;overall='PATCH_BLOCKED';reason='NO_TARGETS';targets=@()})
    Write-Host "PATCH_BLOCKED: no language_server.exe targets found. Receipt: $receipt"
    exit 20
}

$plans = New-Object System.Collections.Generic.List[object]
foreach ($target in $targets) {
    try {
        $publicTarget = Normalize-Path $target
        $arch = Get-PeArchitecture $target
        $version = Get-ProductVersion $target
        $hash = Get-Sha256 $target
        $compat = Find-Compatibility $manifest $version $arch $hash
        $stateRecord = Find-StateRecord $patchState $publicTarget $version $arch $hash
        $sig = $null
        $state = 'UNKNOWN'
        $offset = $null
        $authority = 'none'

        if ($compat) {
            $sig = Get-Signature $manifest ([string]$compat.signature_id)
            if (-not $sig) { throw 'compatibility references missing signature' }
            $ss = Get-SignatureState ([IO.File]::ReadAllBytes($target)) $sig
            $state = $ss.State; $offset=$ss.Offset; $authority='manifest-source'
        } elseif ($stateRecord) {
            $sig = Get-Signature $manifest ([string]$stateRecord.signature_id)
            if (-not $sig) { throw 'patch-state references missing signature' }
            $ss = Get-SignatureState ([IO.File]::ReadAllBytes($target)) $sig
            $state = $ss.State; $offset=$ss.Offset
            if ($state -ne 'PATCHED') { throw 'patch-state hash matched but patched signature is absent' }
            $authority='patch-state'
        } else {
            foreach ($candidate in @($manifest.signatures | Where-Object { [string]$_.architecture -eq $arch })) {
                $ss = Get-SignatureState ([IO.File]::ReadAllBytes($target)) $candidate
                if ($ss.State -ne 'UNKNOWN') { $sig=$candidate; $state=$ss.State; $offset=$ss.Offset; break }
            }
        }

        $authorized = [bool]($compat -or $stateRecord)
        $plans.Add([pscustomobject]@{
            Target=$target;PublicTarget=$publicTarget;Version=$version;Arch=$arch;Hash=$hash;
            Compat=$compat;StateRecord=$stateRecord;Signature=$sig;State=$state;Offset=$offset;
            Authorized=$authorized;Authority=$authority;Backup=$null
        })
    } catch {
        $plans.Add([pscustomobject]@{
            Target=$target;PublicTarget=(Normalize-Path $target);Version='unknown';Arch='unknown';Hash='';
            Compat=$null;StateRecord=$null;Signature=$null;State='ERROR';Offset=$null;
            Authorized=$false;Authority='none';Backup=$null;Error=(Normalize-Text $_.Exception.Message)
        })
    }
}

if ($Mode -eq 'status') {
    foreach ($p in $plans) {
        $status = if ($p.Authorized -and $p.State -eq 'PATCHED') {'PATCHED_VERIFIED'} elseif ($p.Authorized -and $p.State -eq 'ORIGINAL') {'READY'} else {'PATCH_INCOMPATIBLE / BLOCKED'}
        Write-Host "$status | $($p.Version) | $($p.Arch) | $($p.PublicTarget)"
        $results.Add([ordered]@{
            target=$p.PublicTarget;version=$p.Version;architecture=$p.Arch;sha256=$p.Hash;
            state=$p.State;authorized=$p.Authorized;authority=$p.Authority;result=$status
        })
    }
    $overall = if (@($results | Where-Object { $_.result -like '*BLOCKED*' }).Count) {'PATCH_BLOCKED'} else {'OK'}
    $receipt = Write-Receipt ([ordered]@{schema=1;time=(Get-Date).ToString('o');mode='status';overall=$overall;targets=@($results)})
    Write-Host "Receipt: $receipt"
    exit $(if($overall -eq 'OK'){0}else{21})
}

if (Test-ConsumerRunning) {
    $receipt = Write-Receipt ([ordered]@{schema=1;time=(Get-Date).ToString('o');mode=$Mode;overall='PATCH_BLOCKED';reason='PROCESS_RUNNING';targets=@()})
    Write-Host "PATCH_BLOCKED: Antigravity consumer process is running. Receipt: $receipt"
    exit 22
}

if ($Mode -eq 'restore') {
    $restoreFailures = New-Object System.Collections.Generic.List[string]
    foreach ($p in $plans) {
        if ($p.StateRecord) {
            try {
                $backup = [string]$p.StateRecord.backup
                $sourceHash = [string]$p.StateRecord.source_sha256
                Restore-Verified $p.Target $backup $sourceHash
                $patchState.records = @($patchState.records | Where-Object { [string]$_.target -ne $p.PublicTarget })
                Write-Host "RESTORED: $($p.PublicTarget)"
            } catch { $restoreFailures.Add((Normalize-Text $_.Exception.Message)) }
        }
    }
    Save-PatchState $patchState
    if ($restoreFailures.Count) { throw ($restoreFailures -join '; ') }
    exit 0
}

$blocked = @($plans | Where-Object { -not $_.Authorized -or $_.State -notin @('ORIGINAL','PATCHED') })
if ($blocked.Count) {
    foreach ($p in $blocked) { Write-Host "PATCH_INCOMPATIBLE / BLOCKED | $($p.Version) | $($p.Arch) | $($p.PublicTarget) | $($p.Hash)" }
    $receipt = Write-Receipt ([ordered]@{
        schema=1;time=(Get-Date).ToString('o');mode='patch';overall='PATCH_BLOCKED';reason='INCOMPATIBLE_TARGET';
        targets=@($blocked | ForEach-Object {[ordered]@{target=$_.PublicTarget;version=$_.Version;architecture=$_.Arch;sha256=$_.Hash;state=$_.State}})
    })
    Write-Host "Receipt: $receipt"
    exit 23
}

# Transaction rule: verify backups for every ORIGINAL target before the first write.
foreach ($p in $plans) {
    if ($p.State -eq 'ORIGINAL') { $p.Backup = New-VerifiedBackup $p.Target $p.Version $p.Hash }
}

$changed = New-Object System.Collections.Generic.List[object]
try {
    foreach ($p in $plans) {
        if ($p.State -eq 'PATCHED') {
            $results.Add([ordered]@{
                target=$p.PublicTarget;version=$p.Version;architecture=$p.Arch;sha256=$p.Hash;
                state='PATCHED';authority=$p.Authority;result='ALREADY_PATCHED_VERIFIED'
            })
            continue
        }

        $data = [IO.File]::ReadAllBytes($p.Target)
        $fix = Convert-HexBytes ([string]$p.Signature.fix_hex)
        $start = [int]$p.Offset + [int]$p.Signature.write_offset
        if ($start -lt 0 -or $start + $fix.Length -gt $data.Length) { throw "Patch range invalid: $($p.PublicTarget)" }
        [Array]::Copy($fix,0,$data,$start,$fix.Length)
        $changed.Add($p)
        [IO.File]::WriteAllBytes($p.Target,$data)

        $verify = Get-SignatureState ([IO.File]::ReadAllBytes($p.Target)) $p.Signature
        if ($verify.State -ne 'PATCHED') { throw "Post-write verify failed: $($p.PublicTarget)" }
        $after = Get-Sha256 $p.Target
        if ($p.Compat.patched_sha256 -and [string]$p.Compat.patched_sha256 -ne $after) { throw "Patched SHA256 mismatch: $($p.PublicTarget)" }

        $record = [pscustomobject][ordered]@{
            target=$p.PublicTarget;version=$p.Version;architecture=$p.Arch;
            source_sha256=$p.Hash;patched_sha256=$after;signature_id=[string]$p.Signature.id;
            backup=$p.Backup;authority='native-manifest';patched_at=(Get-Date).ToString('o')
        }
        Upsert-StateRecord $patchState $record
        Save-PatchState $patchState

        $results.Add([ordered]@{
            target=$p.PublicTarget;version=$p.Version;architecture=$p.Arch;source_sha256=$p.Hash;
            patched_sha256=$after;signature_id=$p.Signature.id;result='PATCHED_VERIFIED'
        })
    }
} catch {
    $why = Normalize-Text $_.Exception.Message
    $rollbackErrors = New-Object System.Collections.Generic.List[string]
    foreach ($p in @($changed)) {
        try {
            Restore-Verified $p.Target $p.Backup $p.Hash
            $patchState.records = @($patchState.records | Where-Object { [string]$_.target -ne $p.PublicTarget })
        } catch { $rollbackErrors.Add((Normalize-Text $_.Exception.Message)) }
    }
    Save-PatchState $patchState
    $overall = if ($rollbackErrors.Count) {'ROLLBACK_FAILED'} else {'ROLLED_BACK_VERIFIED'}
    $receipt = Write-Receipt ([ordered]@{
        schema=1;time=(Get-Date).ToString('o');mode='patch';overall=$overall;reason=$why;
        rollback_errors=@($rollbackErrors);targets=@($results)
    })
    Write-Host "PATCH FAILED; rollback result=$overall. Receipt: $receipt"
    exit 24
}

$receipt = Write-Receipt ([ordered]@{schema=1;time=(Get-Date).ToString('o');mode='patch';overall='PATCH_VERIFIED';targets=@($results)})
Write-Host "PATCH_VERIFIED. Receipt: $receipt"
exit 0
