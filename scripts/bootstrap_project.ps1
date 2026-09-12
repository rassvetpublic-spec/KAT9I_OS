<#
.SYNOPSIS
Единая точка подготовки GitHub-проекта по стандарту KAT9I.
.DESCRIPTION
Настраивает или проверяет параметры репозитория, метки, переносимые шаблоны, GitHub Project V2 и защиту ветки main.
Режимы: Установка / Статус / Восстановление. Режим «Статус» ничего не меняет. Неизвестные пользовательские файлы и потенциально разрушительные расхождения сохраняются или блокируются; значения секретов никогда не читаются и не выводятся.
#>
[CmdletBinding()]
param(
  [string]$Owner='rassvetpublic-spec',
  [Parameter(Mandatory=$true)][string]$Repository,
  [ValidateSet('Установка','Статус','Восстановление')][string]$Mode='Установка',
  [string]$ManifestPath=(Join-Path $PSScriptRoot '../config/project_bootstrap_standard.json'),
  [int]$ProjectNumber=0,
  [switch]$CreateRepository,
  [ValidateSet('Публичный','Приватный')][string]$Visibility='Приватный',
  [string]$ReceiptPath=''
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Utf8NoBom=[Text.UTF8Encoding]::new($false)
$RepoFull="$Owner/$Repository"
$ReadOnly=($Mode -eq 'Статус')
$Events=[Collections.Generic.List[object]]::new()
$script:RepositoryCreated=$false

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
  if($LASTEXITCODE -ne 0){throw "Ошибка GitHub CLI: gh $($Arguments -join ' ')"}
  $text=($raw -join "`n")
  if([string]::IsNullOrWhiteSpace($text)){return $null}
  return ($text|ConvertFrom-Json -Depth 60)
}

function Rest([string]$Endpoint,[string]$Method='GET',$Body=$null){
  $args=@('api','--method',$Method,'-H','Accept: application/vnd.github+json','-H','X-GitHub-Api-Version: 2022-11-28',$Endpoint)
  return Invoke-GhJson $args $Body
}

function Require-Tools {
  if($PSVersionTable.PSEdition -ne 'Core' -or $PSVersionTable.PSVersion.Major -lt 7){throw 'ЗАБЛОКИРОВАНО: требуется PowerShell 7.'}
  foreach($cmd in @('git','gh')){if(-not(Get-Command $cmd -ErrorAction SilentlyContinue)){throw "ЗАБЛОКИРОВАНО: обязательный инструмент '$cmd' не найден."}}
  $null=& gh auth status 2>&1
  if($LASTEXITCODE -ne 0){throw 'ЗАБЛОКИРОВАНО: GitHub CLI не авторизован.'}
  Add-Event 'GHB0' 'ПРОЙДЕНО' 'PowerShell 7, git и gh доступны; авторизация GitHub действительна.'
}

function Get-RepoOrCreate {
  $repo=$null
  try {$repo=Rest "repos/$RepoFull"} catch {}
  if($repo){return $repo}
  if($ReadOnly -or -not $CreateRepository){throw "ЗАБЛОКИРОВАНО: репозиторий $RepoFull не существует или недоступен; для нового репозитория используйте режим «Установка» с параметром -CreateRepository."}
  $flag=if($Visibility -eq 'Публичный'){'--public'}else{'--private'}
  $null=& gh repo create $RepoFull $flag --add-readme
  if($LASTEXITCODE -ne 0){throw "ЗАБЛОКИРОВАНО: не удалось создать репозиторий $RepoFull."}
  $script:RepositoryCreated=$true
  $repo=Rest "repos/$RepoFull"
  if([string]$repo.default_branch -ne 'main'){
    $old=[uri]::EscapeDataString([string]$repo.default_branch)
    $null=Rest "repos/$RepoFull/branches/$old/rename" 'POST' @{new_name='main'}
    $repo=Rest "repos/$RepoFull"
    if([string]$repo.default_branch -ne 'main'){throw 'ОШИБКА_ПРОВЕРКИ: новый репозиторий не удалось перевести на ветку main.'}
  }
  Add-Event 'GHB0' 'ПРОЙДЕНО' "Репозиторий $RepoFull создан с начальным коммитом и веткой main."
  return $repo
}

function Test-Admin($Repo){
  if(-not $Repo.permissions -or -not [bool]$Repo.permissions.admin){throw 'ЗАБЛОКИРОВАНО: для полной подготовки нужны административные права на репозиторий.'}
}

function Ensure-RepositoryBaseline($Repo,$Manifest){
  $desired=$Manifest.repository
  if([string]$Repo.default_branch -ne [string]$desired.default_branch){
    throw "ЗАБЛОКИРОВАНО: ветка по умолчанию '$($Repo.default_branch)', ожидается '$($desired.default_branch)'. Для существующего репозитория переименование намеренно не выполняется автоматически."
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
    if($ReadOnly){throw "РАСХОЖДЕНИЕ: настройки репозитория отличаются: $(($drift)-join ', ')."}
    $body=@{}
    foreach($k in $checks.Keys){$body[$k]=$checks[$k]}
    $null=Rest "repos/$RepoFull" 'PATCH' $body
    $verify=Rest "repos/$RepoFull"
    foreach($k in $checks.Keys){
      $prop=$verify.PSObject.Properties[$k]
      if($null -eq $prop -or [bool]$prop.Value -ne [bool]$checks[$k]){throw "ОШИБКА_ПРОВЕРКИ: параметр репозитория '$k' не применился."}
    }
  }
  Add-Event 'GHB1' 'ПРОЙДЕНО' 'Базовые настройки репозитория соответствуют манифесту.'
}

function Get-AllLabels {
  $result=@()
  for($page=1;$page -le 20;$page++){
    $batch=@(Rest "repos/$RepoFull/labels?per_page=100&page=$page")
    $result+=@($batch)
    if($batch.Count -lt 100){return @($result)}
  }
  throw 'ЗАБЛОКИРОВАНО: список меток слишком велик для доказуемо полного чтения.'
}

function Ensure-Labels($Manifest){
  $existing=@(Get-AllLabels)
  foreach($d in @($Manifest.labels)){
    $known=@([string]$d.name)
    if($d.PSObject.Properties['legacy_names']){$known+=@($d.legacy_names|ForEach-Object{[string]$_})}
    $m=@($existing|Where-Object{$known -ccontains [string]$_.name})
    if($m.Count -gt 1){throw "ЗАБЛОКИРОВАНО: для русской метки '$($d.name)' одновременно найдены несколько известных вариантов: $(($m.name)-join ', '). Автоматическое объединение не выполняется."}
    if($m.Count -eq 0){
      if($ReadOnly){throw "РАСХОЖДЕНИЕ: отсутствует метка '$($d.name)'."}
      $null=Rest "repos/$RepoFull/labels" 'POST' @{name=$d.name;color=$d.color;description=$d.description}
      continue
    }
    $e=$m[0]
    if([string]$e.name -cne [string]$d.name -or ([string]$e.color).ToLowerInvariant() -ne ([string]$d.color).ToLowerInvariant() -or [string]$e.description -ne [string]$d.description){
      if($ReadOnly){throw "РАСХОЖДЕНИЕ: метка '$($e.name)' требует безопасной миграции в '$($d.name)'."}
      $encoded=[uri]::EscapeDataString([string]$e.name)
      $null=Rest "repos/$RepoFull/labels/$encoded" 'PATCH' @{new_name=$d.name;color=$d.color;description=$d.description}
    }
  }
  $verify=@(Get-AllLabels)
  foreach($d in @($Manifest.labels)){
    $canonical=@($verify|Where-Object{$_.name -ceq [string]$d.name})
    if($canonical.Count -ne 1){throw "ОШИБКА_ПРОВЕРКИ: русская метка '$($d.name)' должна существовать ровно один раз."}
    if($d.PSObject.Properties['legacy_names']){
      $legacy=@($verify|Where-Object{@($d.legacy_names) -ccontains [string]$_.name})
      if($legacy.Count -gt 0){throw "ОШИБКА_ПРОВЕРКИ: после миграции остались старые английские варианты метки '$($d.name)': $(($legacy.name)-join ', ')."}
    }
  }
  Add-Event 'GHB3' 'ПРОЙДЕНО' 'Канонические метки приведены к русскому стандарту; неизвестные пользовательские метки сохранены.'
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
  $body=@{message='служебное: применить стандартную подготовку проекта KAT9I';content=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Content));branch='main'}
  if($Existing){$body.sha=$Existing.sha}
  try {
    $null=Rest "repos/$RepoFull/contents/$encoded" 'PUT' $body
  } catch {
    throw "ЗАБЛОКИРОВАНО: не удалось записать стандартный файл '$Target' в main. Если main уже защищён, изменения файлов должны пройти через отдельный запрос на слияние; защита ветки автоматически не ослабляется. Исходная ошибка: $($_.Exception.Message)"
  }
}

function Ensure-Templates($Manifest){
  $root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
  foreach($t in @($Manifest.templates)){
    $source=[IO.Path]::GetFullPath((Join-Path $root ([string]$t.source)))
    if(-not $source.StartsWith($root,[StringComparison]::OrdinalIgnoreCase)){throw "ЗАБЛОКИРОВАНО: путь шаблона выходит за корень подготовки: $($t.source)"}
    if(-not(Test-Path -LiteralPath $source -PathType Leaf)){throw "ЗАБЛОКИРОВАНО: отсутствует исходный шаблон '$($t.source)'."}
    $desired=Render-Template $source
    $existing=Get-RemoteFile ([string]$t.target)
    if(-not $existing){
      if($ReadOnly){throw "РАСХОЖДЕНИЕ: отсутствует стандартный файл '$($t.target)'."}
      Put-RemoteFile ([string]$t.target) $desired
      continue
    }
    $current=Decode-RemoteContent $existing
    if($current -ceq $desired){continue}
    $managed=($current -match 'KAT9I_PROJECT_BOOTSTRAP/1')
    if($Mode -eq 'Восстановление' -and $managed){
      Put-RemoteFile ([string]$t.target) $desired $existing
      continue
    }
    Add-Event 'GHB2' 'ПОЛЬЗОВАТЕЛЬСКИЙ' "Существующий пользовательский файл '$($t.target)' сохранён; подготовка его не перезаписала."
  }
  Add-Event 'GHB2' 'ПРОЙДЕНО' 'Переносимые стандартные файлы установлены; существующие пользовательские файлы сохранены.'
}

function Get-ProjectNumber($Manifest){
  if($ProjectNumber -gt 0){return $ProjectNumber}
  $title=([string]$Manifest.project.title_template).Replace('{repo}',$Repository)
  $raw=& gh project list --owner $Owner --limit 100 --format json
  if($LASTEXITCODE -ne 0){throw 'ЗАБЛОКИРОВАНО: не удалось получить список GitHub Projects; авторизации gh нужен доступ project.'}
  $list=($raw -join "`n")|ConvertFrom-Json
  $projects=if($list.projects){@($list.projects)}else{@($list)}
  $matches=@($projects|Where-Object{$_.title -ceq $title})
  if($matches.Count -gt 1){throw "ЗАБЛОКИРОВАНО: найдено несколько Project с названием '$title'."}
  if($matches.Count -eq 1){return [int]$matches[0].number}
  if($ReadOnly){throw "РАСХОЖДЕНИЕ: Project '$title' не существует."}
  $raw=& gh project create --owner $Owner --title $title --format json
  if($LASTEXITCODE -ne 0){throw "ЗАБЛОКИРОВАНО: не удалось создать Project '$title'."}
  $created=($raw -join "`n")|ConvertFrom-Json
  if(-not $created.number){throw 'ОШИБКА_ПРОВЕРКИ: в ответе после создания Project отсутствует его номер.'}
  Add-Event 'GHB4' 'ПРОЙДЕНО' "Project '$title' создан."
  return [int]$created.number
}

function Ensure-Project($Manifest){
  $number=Get-ProjectNumber $Manifest
  $title=([string]$Manifest.project.title_template).Replace('{repo}',$Repository)
  $script=Join-Path $PSScriptRoot 'configure_standard_project.ps1'
  $raw=& $script -Owner $Owner -Repository $Repository -ProjectNumber $number -ProjectTitle $title -ViewsPolicyPath (Join-Path ([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))) ([string]$Manifest.project.views_policy)) -Mode $Mode
  if($LASTEXITCODE -ne 0){throw 'ЗАБЛОКИРОВАНО: настройка Project завершилась ошибкой.'}
  Add-Event 'GHB4' 'ПРОЙДЕНО' "Project #$number связан с репозиторием и проверен: канонические поля, итерация 3 дня и 8 русских представлений."
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
  if($matches.Count -gt 1){throw "ЗАБЛОКИРОВАНО: набор правил '$($Manifest.ruleset.name)' продублирован."}
  $body=New-RulesetBody $Manifest
  if($matches.Count -eq 0){
    if($ReadOnly){throw "РАСХОЖДЕНИЕ: набор правил '$($Manifest.ruleset.name)' отсутствует."}
    $null=Rest "repos/$RepoFull/rulesets" 'POST' $body
  } else {
    $detail=Rest "repos/$RepoFull/rulesets/$($matches[0].id)"
    if(-not(Test-Ruleset $detail $Manifest)){
      if($ReadOnly){throw "РАСХОЖДЕНИЕ: набор правил '$($Manifest.ruleset.name)' отличается от стандарта."}
      $null=Rest "repos/$RepoFull/rulesets/$($matches[0].id)" 'PUT' $body
    }
  }
  $verify=@(Rest "repos/$RepoFull/rulesets")|Where-Object{$_.name -ceq [string]$Manifest.ruleset.name}|Select-Object -First 1
  if(-not $verify){throw 'ОШИБКА_ПРОВЕРКИ: после применения отсутствует набор правил защиты main.'}
  $detail=Rest "repos/$RepoFull/rulesets/$($verify.id)"
  if(-not(Test-Ruleset $detail $Manifest)){throw 'ОШИБКА_ПРОВЕРКИ: набор правил защиты main не соответствует стандарту после применения.'}
  Add-Event 'GHB5' 'ПРОЙДЕНО' "Набор правил '$($Manifest.ruleset.name)' проверен."
}

function Audit-Capabilities($Manifest){
  $secretNames=@()
  $secretAuditOk=$true
  try {
    $raw=& gh secret list --repo $RepoFull --json name
    if($LASTEXITCODE -ne 0){$secretAuditOk=$false}
    elseif($raw){$secretNames=@((($raw -join "`n")|ConvertFrom-Json)|ForEach-Object{$_.name})}
  } catch {$secretAuditOk=$false}
  if(-not $secretAuditOk){
    Add-Event 'GHB6' 'НЕ_ПРОВЕРЕНО' 'Не удалось получить список имён секретов. Значения секретов не читались; необязательные возможности не считаются подтверждёнными.'
  } else {
    foreach($name in @($Manifest.capabilities.optional_secret_names)){
      $status=if($secretNames -contains [string]$name){'ЕСТЬ'}else{'НЕОБЯЗАТЕЛЬНЫЙ_ОТСУТСТВУЕТ'}
      Add-Event 'GHB6' $status "Секрет репозитория '$name': $status. Значение секрета не читалось."
    }
    Add-Event 'GHB6' 'ПРОЙДЕНО' 'Возможности проверены без чтения значений секретов.'
  }
}

function Emit-Receipt([string]$Status,[int]$Number,[string]$ErrorMessage=''){
  $receipt=[ordered]@{
    schema='KAT9I_PROJECT_BOOTSTRAP_RECEIPT/1';
    timestamp_utc=(Get-Date).ToUniversalTime().ToString('o');
    status=$Status;mode=$Mode;owner=$Owner;repository=$Repository;project_number=$Number;
    manifest_schema=$Manifest.schema;profile=$Manifest.profile;
    events=@($Events);error=$ErrorMessage;
    secret_values_included=$false;owner_gate='mtd';auto_merge=$false;
    язык='русский'
  }
  $json=$receipt|ConvertTo-Json -Depth 20
  if($ReceiptPath){
    $dir=Split-Path -Parent $ReceiptPath
    if($dir){New-Item -ItemType Directory -Force -Path $dir|Out-Null}
    [IO.File]::WriteAllText([IO.Path]::GetFullPath($ReceiptPath),$json,$Utf8NoBom)
  }
  Write-Output $json
}

if(-not(Test-Path -LiteralPath $ManifestPath -PathType Leaf)){throw "Манифест не найден: $ManifestPath"}
$Manifest=Get-Content $ManifestPath -Raw -Encoding utf8|ConvertFrom-Json -Depth 60
if($Manifest.schema -ne 'KAT9I_PROJECT_BOOTSTRAP/1'){throw "Неподдерживаемая схема манифеста подготовки: $($Manifest.schema)"}

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
  Add-Event 'GHB7' 'ПРОЙДЕНО' 'Настройки репозитория, файлы, метки, Project и защита main прошли повторное чтение и проверку.'
  Emit-Receipt 'ПРОЙДЕНО' $resolvedProject
  exit 0
} catch {
  Add-Event 'GHB7' 'ЗАБЛОКИРОВАНО' $_.Exception.Message
  Emit-Receipt 'ЗАБЛОКИРОВАНО' $resolvedProject $_.Exception.Message
  exit 2
}