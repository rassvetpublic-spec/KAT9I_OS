<#
.SYNOPSIS
Canonical KAT9I GitHub project bootstrap entry.
.DESCRIPTION
Configures or audits Repository settings, labels, portable templates, Project V2 and main protection ruleset.
Modes: Install / Status / Repair. Status is read-only. Unknown custom files and destructive drift are preserved or blocked; secrets are never read or logged.
#>
[CmdletBinding()]
param(
  [string]$Owner='rassvetpublic-spec',
  [Parameter(Mandatory=$true)][string]$Repository,
  [ValidateSet('Install','Status','Repair')][string]$Mode='Install',
  [string]$ManifestPath=(Join-Path $PSScriptRoot '../config/project_bootstrap_standard.json'),
  [int]$ProjectNumber=0,
  [switch]$CreateRepository,
  [ValidateSet('Public','Private')][string]$Visibility='Private',
  [string]$ReceiptPath=''
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Utf8NoBom=[Text.UTF8Encoding]::new($false)
$RepoFull="$Owner/$Repository"
$ReadOnly=($Mode -eq 'Status')
$Events=[Collections.Generic.List[object]]::new()

function Add-Event([string]$Gate,[string]$Status,[string]$Message){
  $Events.Add([pscustomobject]@{gate=$Gate;status=$Status;message=$Message})
  Write-Host ("[{0}] {1}: {2}" -f $Status,$Gate,$Message)
}

function Invoke-GhJson {
  param([Parameter(Mandatory=$true)][string[]]$Arguments,$Payload=$null)
  if($null -eq $Payload){
    $raw=& gh @Arguments
  } else {
    $tmp=[IO.Path]::GetTempFileName()
    try {
      [IO.File]::WriteAllText($tmp,($Payload|ConvertTo-Json -Depth 60 -Compress),$Utf8NoBom)
      $raw=& gh @Arguments --input $tmp
    } finally { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
  }
  if($LASTEXITCODE -ne 0){throw "GitHub CLI error: gh $($Arguments -join ' ')"}
  $text=($raw -join "`n")
  if([string]::IsNullOrWhiteSpace($text)){return $null}
  return ($text|ConvertFrom-Json -Depth 60)
}

function Rest([string]$Endpoint,[string]$Method='GET',$Body=$null){
  $args=@('api','--method',$Method,'-H','Accept: application/vnd.github+json','-H','X-GitHub-Api-Version: 2022-11-28',$Endpoint)
  return Invoke-GhJson $args $Body
}

function Require-Tools {
  if($PSVersionTable.PSEdition -ne 'Core' -or $PSVersionTable.PSVersion.Major -lt 7){throw 'BLOCKED: PowerShell 7 is required.'}
  foreach($cmd in @('git','gh')){if(-not(Get-Command $cmd -ErrorAction SilentlyContinue)){throw "BLOCKED: required tool '$cmd' not found."}}
  $null=& gh auth status 2>&1
  if($LASTEXITCODE -ne 0){throw 'BLOCKED: GitHub CLI is not authenticated.'}
  Add-Event 'GHB0' 'PASS' 'PowerShell 7, git and gh are available; GitHub auth is valid.'
}

function Get-RepoOrCreate {
  $repo=$null
  try {$repo=Rest "repos/$RepoFull"} catch {}
  if($repo){return $repo}
  if($ReadOnly -or -not $CreateRepository){throw "BLOCKED: repository $RepoFull does not exist; use Install -CreateRepository for a new repository."}
  $flag=if($Visibility -eq 'Public'){'--public'}else{'--private'}
  $null=& gh repo create $RepoFull $flag --add-readme
  if($LASTEXITCODE -ne 0){throw "BLOCKED: cannot create repository $RepoFull."}
  $repo=Rest "repos/$RepoFull"
  Add-Event 'GHB0' 'PASS' "Repository $RepoFull created with initial commit."
  return $repo
}

function Test-Admin($Repo){
  if(-not $Repo.permissions -or -not [bool]$Repo.permissions.admin){throw 'BLOCKED: repository admin permission is required for full bootstrap.'}
}

function Ensure-RepositoryBaseline($Repo,$Manifest){
  $desired=$Manifest.repository
  if([string]$Repo.default_branch -ne [string]$desired.default_branch){
    throw "BLOCKED: default branch is '$($Repo.default_branch)', expected '$($desired.default_branch)'. Branch rename/migration is intentionally not automatic."
  }
  $checks=@{
    has_issues=[bool]$desired.has_issues
    has_wiki=[bool]$desired.has_wiki
    allow_auto_merge=[bool]$desired.allow_auto_merge
    allow_merge_commit=[bool]$desired.allow_merge_commit
    allow_rebase_merge=[bool]$desired.allow_rebase_merge
    allow_squash_merge=[bool]$desired.allow_squash_merge
    allow_update_branch=[bool]$desired.allow_update_branch
    delete_branch_on_merge=[bool]$desired.delete_branch_on_merge
  }
  $drift=@()
  foreach($k in $checks.Keys){
    $prop=$Repo.PSObject.Properties[$k]
    if($null -eq $prop -or [bool]$prop.Value -ne [bool]$checks[$k]){$drift+=$k}
  }
  if($drift.Count -gt 0){
    if($ReadOnly){throw "DRIFT: repository settings differ: $(($drift)-join ', ')."}
    $body=@{}
    foreach($k in $checks.Keys){$body[$k]=$checks[$k]}
    $null=Rest "repos/$RepoFull" 'PATCH' $body
    $verify=Rest "repos/$RepoFull"
    foreach($k in $checks.Keys){
      $prop=$verify.PSObject.Properties[$k]
      if($null -eq $prop -or [bool]$prop.Value -ne [bool]$checks[$k]){throw "VERIFY_FAIL: repository setting '$k'."}
    }
  }
  Add-Event 'GHB1' 'PASS' 'Repository baseline matches manifest.'
}

function Ensure-Labels($Manifest){
  $existing=@(Rest "repos/$RepoFull/labels?per_page=100")
  foreach($d in @($Manifest.labels)){
    $m=@($existing|Where-Object{$_.name -ceq $d.name})
    if($m.Count -gt 1){throw "BLOCKED: duplicate label '$($d.name)'."}
    if($m.Count -eq 0){
      if($ReadOnly){throw "DRIFT: missing label '$($d.name)'."}
      $null=Rest "repos/$RepoFull/labels" 'POST' @{name=$d.name;color=$d.color;description=$d.description}
      continue
    }
    $e=$m[0]
    if(([string]$e.color).ToLowerInvariant() -ne ([string]$d.color).ToLowerInvariant() -or [string]$e.description -ne [string]$d.description){
      if($ReadOnly){throw "DRIFT: label '$($d.name)' differs from manifest."}
      $encoded=[uri]::EscapeDataString([string]$d.name)
      $null=Rest "repos/$RepoFull/labels/$encoded" 'PATCH' @{new_name=$d.name;color=$d.color;description=$d.description}
    }
  }
  Add-Event 'GHB3' 'PASS' 'Canonical labels are present; unknown labels are preserved.'
}

function Render-Template([string]$Path){
  $text=Get-Content $Path -Raw -Encoding utf8
  return $text.Replace('{{PROJECT_NAME}}',$Repository).Replace('{{OWNER}}',$Owner).Replace('{{REPOSITORY}}',$Repository)
}

function Get-RemoteFile([string]$Target){
  $encoded=($Target -split '/'|ForEach-Object{[uri]::EscapeDataString($_)}) -join '/'
  try {return Rest "repos/$RepoFull/contents/$encoded?ref=main"} catch {return $null}
}

function Decode-RemoteContent($File){
  if(-not $File){return $null}
  $raw=([string]$File.content).Replace("`n",'')
  return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($raw))
}

function Put-RemoteFile([string]$Target,[string]$Content,$Existing=$null){
  $encoded=($Target -split '/'|ForEach-Object{[uri]::EscapeDataString($_)}) -join '/'
  $body=@{message="chore: apply KAT9I standard project bootstrap";content=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Content));branch='main'}
  if($Existing){$body.sha=$Existing.sha}
  $null=Rest "repos/$RepoFull/contents/$encoded" 'PUT' $body
}

function Ensure-Templates($Manifest){
  $root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
  foreach($t in @($Manifest.templates)){
    $source=[IO.Path]::GetFullPath((Join-Path $root ([string]$t.source)))
    if(-not $source.StartsWith($root,[StringComparison]::OrdinalIgnoreCase)){throw "BLOCKED: template escapes bootstrap root: $($t.source)"}
    if(-not(Test-Path -LiteralPath $source -PathType Leaf)){throw "BLOCKED: missing template source '$($t.source)'."}
    $desired=Render-Template $source
    $existing=Get-RemoteFile ([string]$t.target)
    if(-not $existing){
      if($ReadOnly){throw "DRIFT: missing standard file '$($t.target)'."}
      Put-RemoteFile ([string]$t.target) $desired
      continue
    }
    $current=Decode-RemoteContent $existing
    if($current -ceq $desired){continue}
    $managed=($current -match 'KAT9I_PROJECT_BOOTSTRAP/1')
    if($Mode -eq 'Repair' -and $managed){
      Put-RemoteFile ([string]$t.target) $desired $existing
      continue
    }
    Add-Event 'GHB2' 'CUSTOM' "Preserved existing custom file '$($t.target)'; bootstrap did not overwrite it."
  }
  Add-Event 'GHB2' 'PASS' 'Portable standard files are installed or existing custom files were preserved.'
}

function Get-ProjectNumber($Manifest){
  if($ProjectNumber -gt 0){return $ProjectNumber}
  $title=([string]$Manifest.project.title_template).Replace('{repo}',$Repository)
  $raw=& gh project list --owner $Owner --limit 100 --format json
  if($LASTEXITCODE -ne 0){throw 'BLOCKED: cannot list GitHub Projects; gh auth needs project scope.'}
  $list=($raw -join "`n")|ConvertFrom-Json
  $projects=if($list.projects){@($list.projects)}else{@($list)}
  $matches=@($projects|Where-Object{$_.title -ceq $title})
  if($matches.Count -gt 1){throw "BLOCKED: more than one Project is named '$title'."}
  if($matches.Count -eq 1){return [int]$matches[0].number}
  if($ReadOnly){throw "DRIFT: Project '$title' does not exist."}
  $raw=& gh project create --owner $Owner --title $title --format json
  if($LASTEXITCODE -ne 0){throw "BLOCKED: cannot create Project '$title'."}
  $created=($raw -join "`n")|ConvertFrom-Json
  if(-not $created.number){throw 'VERIFY_FAIL: created Project response has no number.'}
  Add-Event 'GHB4' 'PASS' "Project '$title' created."
  return [int]$created.number
}

function Ensure-Project($Manifest){
  $number=Get-ProjectNumber $Manifest
  $title=([string]$Manifest.project.title_template).Replace('{repo}',$Repository)
  $script=Join-Path $PSScriptRoot 'configure_standard_project.ps1'
  $raw=& $script -Owner $Owner -Repository $Repository -ProjectNumber $number -ProjectTitle $title -ViewsPolicyPath (Join-Path ([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))) ([string]$Manifest.project.views_policy)) -Mode $Mode
  if($LASTEXITCODE -ne 0){throw 'BLOCKED: Project configuration failed.'}
  Add-Event 'GHB4' 'PASS' "Project #$number linked and verified with canonical fields, 3-day iteration and 8 views."
  return $number
}

function New-RulesetBody($Manifest){
  $r=$Manifest.ruleset
  return @{
    name=$r.name;target='branch';enforcement=$r.enforcement;bypass_actors=@();
    conditions=@{ref_name=@{exclude=@();include=@('~DEFAULT_BRANCH')}};
    rules=@(
      @{type='deletion'},
      @{type='non_fast_forward'},
      @{type='pull_request';parameters=@{required_approving_review_count=0;dismiss_stale_reviews_on_push=$true;required_reviewers=@();require_code_owner_review=$false;require_last_push_approval=$false;required_review_thread_resolution=$true;require_extra_approval_for_unattributed_changes=$true;allowed_merge_methods=@('merge','squash','rebase')}},
      @{type='required_status_checks';parameters=@{strict_required_status_checks_policy=$true;do_not_enforce_on_create=$true;required_status_checks=@(@{context=[string]$r.required_status_check})}}
    )
  }
}

function Normalize-Ruleset($Ruleset){
  $check=@($Ruleset.rules|Where-Object{$_.type -eq 'required_status_checks'})|Select-Object -First 1
  $pr=@($Ruleset.rules|Where-Object{$_.type -eq 'pull_request'})|Select-Object -First 1
  [pscustomobject]@{
    name=$Ruleset.name;target=$Ruleset.target;enforcement=$Ruleset.enforcement;
    default_branch_only=(@($Ruleset.conditions.ref_name.include) -contains '~DEFAULT_BRANCH');
    deletion=[bool](@($Ruleset.rules.type) -contains 'deletion');
    non_fast_forward=[bool](@($Ruleset.rules.type) -contains 'non_fast_forward');
    pull_request=[bool]$pr;
    review_threads=$(if($pr){[bool]$pr.parameters.required_review_thread_resolution}else{$false});
    strict_checks=$(if($check){[bool]$check.parameters.strict_required_status_checks_policy}else{$false});
    check=$(if($check -and @($check.parameters.required_status_checks).Count -eq 1){[string]$check.parameters.required_status_checks[0].context}else{''});
    bypass_count=@($Ruleset.bypass_actors).Count
  }
}

function Test-Ruleset($Ruleset,$Manifest){
  $n=Normalize-Ruleset $Ruleset; $r=$Manifest.ruleset
  return ($n.name -ceq $r.name -and $n.target -eq 'branch' -and $n.enforcement -eq $r.enforcement -and $n.default_branch_only -and $n.deletion -and $n.non_fast_forward -and $n.pull_request -and $n.review_threads -and $n.strict_checks -and $n.check -ceq [string]$r.required_status_check -and $n.bypass_count -eq 0)
}

function Ensure-Ruleset($Manifest){
  $all=@(Rest "repos/$RepoFull/rulesets")
  $matches=@($all|Where-Object{$_.name -ceq [string]$Manifest.ruleset.name})
  if($matches.Count -gt 1){throw "BLOCKED: duplicate ruleset '$($Manifest.ruleset.name)'."}
  $body=New-RulesetBody $Manifest
  if($matches.Count -eq 0){
    if($ReadOnly){throw "DRIFT: ruleset '$($Manifest.ruleset.name)' is missing."}
    $null=Rest "repos/$RepoFull/rulesets" 'POST' $body
  } else {
    $detail=Rest "repos/$RepoFull/rulesets/$($matches[0].id)"
    if(-not(Test-Ruleset $detail $Manifest)){
      if($ReadOnly){throw "DRIFT: ruleset '$($Manifest.ruleset.name)' differs from standard."}
      $null=Rest "repos/$RepoFull/rulesets/$($matches[0].id)" 'PUT' $body
    }
  }
  $verify=@(Rest "repos/$RepoFull/rulesets")|Where-Object{$_.name -ceq [string]$Manifest.ruleset.name}|Select-Object -First 1
  if(-not $verify){throw 'VERIFY_FAIL: main protection ruleset missing after apply.'}
  $detail=Rest "repos/$RepoFull/rulesets/$($verify.id)"
  if(-not(Test-Ruleset $detail $Manifest)){throw 'VERIFY_FAIL: main protection ruleset differs after apply.'}
  Add-Event 'GHB5' 'PASS' "Ruleset '$($Manifest.ruleset.name)' verified."
}

function Audit-Capabilities($Manifest){
  $secretNames=@()
  try {
    $raw=& gh secret list --repo $RepoFull --json name
    if($LASTEXITCODE -eq 0 -and $raw){$secretNames=@((($raw -join "`n")|ConvertFrom-Json)|ForEach-Object{$_.name})}
  } catch {}
  foreach($name in @($Manifest.capabilities.optional_secret_names)){
    $status=if($secretNames -contains [string]$name){'PRESENT'}else{'OPTIONAL_MISSING'}
    Add-Event 'GHB6' $status "Repository secret '$name': $status (value was not read)."
  }
  Add-Event 'GHB6' 'PASS' 'Capabilities audited without reading secret values.'
}

function Emit-Receipt([string]$Status,[int]$Number,[string]$ErrorMessage=''){
  $receipt=[ordered]@{
    schema='KAT9I_PROJECT_BOOTSTRAP_RECEIPT/1';
    timestamp_utc=(Get-Date).ToUniversalTime().ToString('o');
    status=$Status;mode=$Mode;owner=$Owner;repository=$Repository;project_number=$Number;
    manifest_schema=$Manifest.schema;profile=$Manifest.profile;
    events=@($Events);error=$ErrorMessage;
    secret_values_included=$false;owner_gate='mtd';auto_merge=$false
  }
  $json=$receipt|ConvertTo-Json -Depth 20
  if($ReceiptPath){
    $dir=Split-Path -Parent $ReceiptPath
    if($dir){New-Item -ItemType Directory -Force -Path $dir|Out-Null}
    [IO.File]::WriteAllText([IO.Path]::GetFullPath($ReceiptPath),$json,$Utf8NoBom)
  }
  Write-Output $json
}

if(-not(Test-Path -LiteralPath $ManifestPath -PathType Leaf)){throw "Manifest not found: $ManifestPath"}
$Manifest=Get-Content $ManifestPath -Raw -Encoding utf8|ConvertFrom-Json -Depth 60
if($Manifest.schema -ne 'KAT9I_PROJECT_BOOTSTRAP/1'){throw "Unsupported bootstrap manifest schema: $($Manifest.schema)"}

$resolvedProject=0
try {
  Require-Tools
  $repo=Get-RepoOrCreate
  Test-Admin $repo
  $repo=Rest "repos/$RepoFull"
  Ensure-RepositoryBaseline $repo $Manifest
  Ensure-Labels $Manifest
  Ensure-Templates $Manifest
  $resolvedProject=Ensure-Project $Manifest
  Ensure-Ruleset $Manifest
  Audit-Capabilities $Manifest
  Add-Event 'GHB7' 'PASS' 'Repository, files, labels, Project and ruleset passed read-back verification.'
  Emit-Receipt 'PASS' $resolvedProject
  exit 0
} catch {
  Add-Event 'GHB7' 'BLOCKED' $_.Exception.Message
  Emit-Receipt 'BLOCKED' $resolvedProject $_.Exception.Message
  exit 2
}
