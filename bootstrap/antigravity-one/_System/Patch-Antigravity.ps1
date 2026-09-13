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

function Get-PeArchitecture([string]$Path) {
    $fs = [IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
    try {
        $br = New-Object IO.BinaryReader($fs)
        if ($br.ReadUInt16() -ne 0x5A4D) { throw 'Not an MZ executable' }
        $fs.Position = 0x3C
        $pe = $br.ReadInt32()
        $fs.Position = $pe
        if ($br.ReadUInt32() -ne 0x00004550) { throw 'Missing PE signature' }
        $machine = $br.ReadUInt16()
        if ($machine -eq 0x8664) { return 'x64' }
        if ($machine -eq 0xAA64) { return 'arm64' }
        return ('unknown-0x{0:X4}' -f $machine)
    } finally { $fs.Dispose() }
}

function Get-ProductVersion([string]$Target) {
    $root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $Target))
    $exe = Join-Path $root 'Antigravity.exe'
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

function Get-Targets {
    $candidates = New-Object System.Collections.Generic.List[string]
    foreach ($p in @(
        (Join-Path $Root 'Standalone\App\resources\bin\language_server.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\antigravity\resources\bin\language_server.exe'),
        (Join-Path $env:ProgramFiles 'Antigravity\resources\bin\language_server.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Antigravity\resources\bin\language_server.exe')
    )) {
        if ($p -and (Test-Path -LiteralPath $p -PathType Leaf)) { $candidates.Add([IO.Path]::GetFullPath($p)) }
    }
    $unique = @($candidates | Sort-Object -Unique)
    return $unique
}

function Test-ConsumerRunning {
    return [bool](Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -in @('Antigravity','language_server','antigravity-tools') })
}

function Load-Manifest {
    if (-not (Test-Path -LiteralPath $ManifestPath)) { throw "Manifest missing: $ManifestPath" }
    $m = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($m.schema -ne 1) { throw 'Unsupported manifest schema' }
    return $m
}

function Find-Compatibility($Manifest,[string]$Version,[string]$Arch,[string]$Hash) {
    @($Manifest.compatibility | Where-Object {
        ([string]$_.product_version -eq $Version) -and ([string]$_.architecture -eq $Arch) -and ([string]$_.source_sha256 -eq $Hash)
    }) | Select-Object -First 1
}

function Get-Signature($Manifest,[string]$Id) {
    @($Manifest.signatures | Where-Object { [string]$_.id -eq $Id }) | Select-Object -First 1
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
    if ($bhash -ne $Hash) { throw "Backup verification failed: $backup" }
    return $backup
}

function Restore-Verified([string]$Target,[string]$Backup,[string]$ExpectedHash) {
    Copy-Item -LiteralPath $Backup -Destination $Target -Force
    if ((Get-Sha256 $Target) -ne $ExpectedHash) { throw "Rollback verification failed: $Target" }
}

$manifest = Load-Manifest
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
        $arch = Get-PeArchitecture $target
        $version = Get-ProductVersion $target
        $hash = Get-Sha256 $target
        $compat = Find-Compatibility $manifest $version $arch $hash
        $sig = $null
        $state = 'UNKNOWN'
        $offset = $null
        if ($compat) {
            $sig = Get-Signature $manifest ([string]$compat.signature_id)
            if (-not $sig) { throw 'compatibility references missing signature' }
            $ss = Get-SignatureState ([IO.File]::ReadAllBytes($target)) $sig
            $state = $ss.State; $offset=$ss.Offset
        } else {
            foreach ($candidate in @($manifest.signatures | Where-Object { [string]$_.architecture -eq $arch })) {
                $ss = Get-SignatureState ([IO.File]::ReadAllBytes($target)) $candidate
                if ($ss.State -ne 'UNKNOWN') { $sig=$candidate; $state=$ss.State; $offset=$ss.Offset; break }
            }
        }
        $authorized = [bool]$compat
        $plans.Add([pscustomobject]@{Target=$target;Version=$version;Arch=$arch;Hash=$hash;Compat=$compat;Signature=$sig;State=$state;Offset=$offset;Authorized=$authorized;Backup=$null})
    } catch {
        $plans.Add([pscustomobject]@{Target=$target;Version='unknown';Arch='unknown';Hash='';Compat=$null;Signature=$null;State='ERROR';Offset=$null;Authorized=$false;Backup=$null;Error=$_.Exception.Message})
    }
}

if ($Mode -eq 'status') {
    foreach ($p in $plans) {
        $publicPath = Normalize-Path $p.Target
        $status = if ($p.State -eq 'PATCHED') {'PATCHED'} elseif ($p.Authorized -and $p.State -eq 'ORIGINAL') {'READY'} else {'PATCH_INCOMPATIBLE / BLOCKED'}
        Write-Host "$status | $($p.Version) | $($p.Arch) | $publicPath"
        $results.Add([ordered]@{target=$publicPath;version=$p.Version;architecture=$p.Arch;sha256=$p.Hash;state=$p.State;authorized=$p.Authorized;result=$status})
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
    foreach ($p in $plans) {
        if (-not $p.Hash) { continue }
        $dir = Join-Path (Join-Path $PatchBackupRoot $p.Version) $p.Hash
        $backup = Join-Path $dir 'language_server.exe'
        if (Test-Path -LiteralPath $backup) { Restore-Verified $p.Target $backup $p.Hash; Write-Host "RESTORED: $(Normalize-Path $p.Target)" }
    }
    exit 0
}

$blocked = @($plans | Where-Object { -not $_.Authorized -or $_.State -notin @('ORIGINAL','PATCHED') })
if ($blocked.Count) {
    foreach ($p in $blocked) { Write-Host "PATCH_INCOMPATIBLE / BLOCKED | $($p.Version) | $($p.Arch) | $(Normalize-Path $p.Target) | $($p.Hash)" }
    $receipt = Write-Receipt ([ordered]@{schema=1;time=(Get-Date).ToString('o');mode='patch';overall='PATCH_BLOCKED';reason='INCOMPATIBLE_TARGET';targets=@($blocked | ForEach-Object {[ordered]@{target=(Normalize-Path $_.Target);version=$_.Version;architecture=$_.Arch;sha256=$_.Hash;state=$_.State}})})
    Write-Host "Receipt: $receipt"
    exit 23
}

# Transaction rule: verify backups for every target before the first write.
foreach ($p in $plans) {
    if ($p.State -eq 'ORIGINAL') { $p.Backup = New-VerifiedBackup $p.Target $p.Version $p.Hash }
}

$changed = New-Object System.Collections.Generic.List[object]
try {
    foreach ($p in $plans) {
        if ($p.State -eq 'PATCHED') {
            $results.Add([ordered]@{target=(Normalize-Path $p.Target);version=$p.Version;architecture=$p.Arch;sha256=$p.Hash;state='PATCHED';result='ALREADY_PATCHED'})
            continue
        }
        $data = [IO.File]::ReadAllBytes($p.Target)
        $fix = [Convert]::FromHexString(([string]$p.Signature.fix_hex -replace '\s',''))
        $start = [int]$p.Offset + [int]$p.Signature.write_offset
        if ($start -lt 0 -or $start + $fix.Length -gt $data.Length) { throw "Patch range invalid: $($p.Target)" }
        [Array]::Copy($fix,0,$data,$start,$fix.Length)
        [IO.File]::WriteAllBytes($p.Target,$data)
        $changed.Add($p)
        $verify = Get-SignatureState ([IO.File]::ReadAllBytes($p.Target)) $p.Signature
        if ($verify.State -ne 'PATCHED') { throw "Post-write verify failed: $($p.Target)" }
        $after = Get-Sha256 $p.Target
        if ($p.Compat.patched_sha256 -and [string]$p.Compat.patched_sha256 -ne $after) { throw "Patched SHA256 mismatch: $($p.Target)" }
        $results.Add([ordered]@{target=(Normalize-Path $p.Target);version=$p.Version;architecture=$p.Arch;source_sha256=$p.Hash;patched_sha256=$after;signature_id=$p.Signature.id;result='PATCHED_VERIFIED'})
    }
} catch {
    $why = $_.Exception.Message
    foreach ($p in @($changed)) { Restore-Verified $p.Target $p.Backup $p.Hash }
    $receipt = Write-Receipt ([ordered]@{schema=1;time=(Get-Date).ToString('o');mode='patch';overall='ROLLED_BACK';reason=$why;targets=@($results)})
    Write-Host "PATCH FAILED; transaction rolled back and verified. Receipt: $receipt"
    exit 24
}

$receipt = Write-Receipt ([ordered]@{schema=1;time=(Get-Date).ToString('o');mode='patch';overall='PATCH_VERIFIED';targets=@($results)})
Write-Host "PATCH_VERIFIED. Receipt: $receipt"
exit 0
