[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Owner,
  [Parameter(Mandatory=$true)][string]$Repository,
  [Parameter(Mandatory=$true)][int]$ProjectNumber,
  [Parameter(Mandatory=$true)][string]$ProjectTitle,
  [string]$ViewsPolicyPath = (Join-Path $PSScriptRoot '../config/project_views.json'),
  [ValidateSet('Install','Status','Repair')][string]$Mode='Install'
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Utf8NoBom=[Text.UTF8Encoding]::new($false)
$script:ReadOnly=($Mode -eq 'Status')

function Invoke-GhJson {
  param([string[]]$Arguments,$Payload=$null)
  if($null -eq $Payload){
    $raw=& gh @Arguments
  } else {
    $tmp=[IO.Path]::GetTempFileName()
    try {
      [IO.File]::WriteAllText($tmp,($Payload|ConvertTo-Json -Depth 50 -Compress),$Utf8NoBom)
      $raw=& gh @Arguments --input $tmp
    } finally { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
  }
  if($LASTEXITCODE -ne 0){throw "GitHub CLI error: gh $($Arguments -join ' ')"}
  $text=($raw -join "`n")
  if([string]::IsNullOrWhiteSpace($text)){return $null}
  return ($text|ConvertFrom-Json -Depth 50)
}

function Gql([string]$Query,[hashtable]$Variables){
  $r=Invoke-GhJson @('api','graphql') @{query=$Query;variables=$Variables}
  if($null -eq $r){throw 'GitHub GraphQL returned empty response.'}
  if($r.PSObject.Properties['errors'] -and $r.errors){
    throw (($r.errors|ForEach-Object{$_.message}) -join '; ')
  }
  return $r
}

function Snapshot {
$q=@'
query($login:String!,$number:Int!,$repo:String!){
 user(login:$login){id projectV2(number:$number){id title url items{totalCount} repositories(first:100){nodes{id nameWithOwner}} fields(first:100){nodes{__typename ... on ProjectV2Field{id name dataType} ... on ProjectV2SingleSelectField{id name dataType options{id name color description}} ... on ProjectV2IterationField{id name dataType configuration{duration startDay}}}} views(first:100){nodes{id name layout filter}}}}
 organization(login:$login){id projectV2(number:$number){id title url items{totalCount} repositories(first:100){nodes{id nameWithOwner}} fields(first:100){nodes{__typename ... on ProjectV2Field{id name dataType} ... on ProjectV2SingleSelectField{id name dataType options{id name color description}} ... on ProjectV2IterationField{id name dataType configuration{duration startDay}}}} views(first:100){nodes{id name layout filter}}}}
 repository(owner:$login,name:$repo){id nameWithOwner}
}
'@
  $d=(Gql $q @{login=$Owner;number=$ProjectNumber;repo=$Repository}).data
  $p=$null
  if($d.user){$p=$d.user.projectV2}
  if(-not $p -and $d.organization){$p=$d.organization.projectV2}
  if(-not $p){throw "Project #$ProjectNumber not found for $Owner."}
  return [pscustomobject]@{project=$p;repository=$d.repository}
}

function Opt([string]$Name,[string]$Color,[string]$Description,[string[]]$Aliases=@()){
  if($Aliases.Count -eq 0){$Aliases=@($Name)}
  [pscustomobject]@{name=$Name;color=$Color;description=$Description;aliases=$Aliases}
}

function Find-Field($Fields,[string[]]$Aliases){
  $m=@(@($Fields)|Where-Object{$Aliases -contains $_.name})
  if($m.Count -gt 1){throw "Ambiguous Project fields: $(($m.name)-join ', ')"}
  if($m.Count -eq 1){return $m[0]}
  return $null
}

function Test-OptionsExact($Field,[object[]]$Defs){
  if(@($Field.options).Count -ne $Defs.Count){return $false}
  foreach($d in $Defs){if(-not (@($Field.options)|Where-Object{$_.name -ceq $d.name})){return $false}}
  return $true
}

function Set-SelectField($Field,[string]$Name,[object[]]$Defs){
$q=@'
mutation($input:UpdateProjectV2FieldInput!){updateProjectV2Field(input:$input){projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}}}
'@
  $opts=@($Defs|ForEach-Object{@{name=$_.name;color=$_.color;description=$_.description}})
  $null=Gql $q @{input=@{fieldId=$Field.id;name=$Name;singleSelectOptions=$opts}}
}

function Ensure-Select([string]$Name,[string[]]$Aliases,[object[]]$Defs){
  $s=Snapshot; $p=$s.project
  $f=Find-Field $p.fields.nodes $Aliases
  if(-not $f){
    if($script:ReadOnly){throw "DRIFT: missing Project field '$Name'."}
$q=@'
mutation($input:CreateProjectV2FieldInput!){createProjectV2Field(input:$input){projectV2Field{... on ProjectV2SingleSelectField{id name}}}}
'@
    $opts=@($Defs|ForEach-Object{@{name=$_.name;color=$_.color;description=$_.description}})
    $null=Gql $q @{input=@{projectId=$p.id;name=$Name;dataType='SINGLE_SELECT';singleSelectOptions=$opts}}
    return
  }
  if($f.__typename -ne 'ProjectV2SingleSelectField'){throw "BLOCKED: '$($f.name)' has incompatible field type."}
  if((Test-OptionsExact $f $Defs) -and ($f.name -ceq $Name -or ($Name -eq 'Статус' -and $f.name -eq 'Status'))){return}
  if($script:ReadOnly){throw "DRIFT: Project field '$Name' differs from standard."}
  if([int]$p.items.totalCount -gt 0){throw "BLOCKED: Project field '$Name' differs and Project already has items; bootstrap will not replace option IDs."}
  Set-SelectField $f $Name $Defs
}

function Ensure-Iteration {
  $s=Snapshot; $p=$s.project
  $f=Find-Field $p.fields.nodes @('Итерация')
  if($f){
    if($f.__typename -ne 'ProjectV2IterationField' -or [int]$f.configuration.duration -ne 3){throw "BLOCKED: Iteration field differs from 3-day standard."}
    return
  }
  if($script:ReadOnly){throw 'DRIFT: missing 3-day Iteration field.'}
$q=@'
mutation($input:CreateProjectV2FieldInput!){createProjectV2Field(input:$input){projectV2Field{... on ProjectV2IterationField{id name}}}}
'@
  $null=Gql $q @{input=@{projectId=$p.id;name='Итерация';dataType='ITERATION';iterationConfiguration=@{startDate=(Get-Date).Date.ToString('yyyy-MM-dd');duration=3;iterations=@()}}}
}

function Ensure-LinkAndTitle {
  $s=Snapshot; $p=$s.project; $repo=$s.repository
  if(-not $repo){throw "Repository $Owner/$Repository not found."}
  if($p.title -cne $ProjectTitle){
    if($script:ReadOnly){throw "DRIFT: Project title '$($p.title)' != '$ProjectTitle'."}
$q=@'
mutation($input:UpdateProjectV2Input!){updateProjectV2(input:$input){projectV2{id title}}}
'@
    $null=Gql $q @{input=@{projectId=$p.id;title=$ProjectTitle}}
  }
  if(-not (@($p.repositories.nodes)|Where-Object{$_.id -eq $repo.id})){
    if($script:ReadOnly){throw 'DRIFT: Project is not linked to repository.'}
$q=@'
mutation($input:LinkProjectV2ToRepositoryInput!){linkProjectV2ToRepository(input:$input){repository{id}}}
'@
    $null=Gql $q @{input=@{projectId=$p.id;repositoryId=$repo.id}}
  }
}

function Ensure-Views {
  $policy=Get-Content $ViewsPolicyPath -Raw -Encoding utf8|ConvertFrom-Json
  $s=Snapshot; $p=$s.project
  $status=Find-Field $p.fields.nodes @('Статус','Status')
  if(-not $status){throw 'Status field is missing.'}
  $desired=@($policy.views|ForEach-Object{[pscustomobject]@{name=$_.name;layout=$_.layout;filter=$_.filter.Replace('{status}',$status.name)}})
  $canonical=@($desired.name)
  $safeLegacy=@('View 1','Table','00 — Все задачи','01 — Готово к работе','02 — В работе','03 — Проверка','04 — Заблокировано')
  $unknown=@($p.views.nodes|Where-Object{$canonical -cnotcontains $_.name -and $safeLegacy -cnotcontains $_.name})
  if($unknown.Count -gt 0){throw "BLOCKED: unknown Project views: $(($unknown.name)-join ', ')."}

  $visible=@()
  foreach($alias in @('Title','Assignees','Status','Статус','Этап','Приоритет','Тип','Область','Размер','Итерация','Исполнитель','Проверяющий','Исполнение','Цель','Риск','Доказательство','Linked pull requests','Sub-issues progress')){
    $f=Find-Field $p.fields.nodes @($alias)
    if($f -and $visible -notcontains $f.id){$visible+=$f.id}
  }

  foreach($v in $desired){
    $existing=@($p.views.nodes|Where-Object{$_.name -ceq $v.name})
    if($existing.Count -gt 1){throw "BLOCKED: duplicate Project view '$($v.name)'."}
    if($existing.Count -eq 1){
      if($existing[0].layout -cne $v.layout -or [string]$existing[0].filter -cne [string]$v.filter){throw "BLOCKED: existing view '$($v.name)' differs from standard."}
      continue
    }
    if($script:ReadOnly){throw "DRIFT: missing Project view '$($v.name)'."}
$q=@'
mutation($input:CreateProjectV2ViewInput!){createProjectV2View(input:$input){projectV2View{id}}}
'@
    $created=Gql $q @{input=@{projectId=$p.id;name=$v.name;layout=$v.layout;configuration=@{visibleFieldIds=$visible}}}
    $id=$created.data.createProjectV2View.projectV2View.id
$q=@'
mutation($input:UpdateProjectV2ViewInput!){updateProjectV2View(input:$input){projectV2View{id}}}
'@
    $cfg=@{viewId=$id;filter=$v.filter}
    if($v.layout -ne 'ROADMAP_LAYOUT'){$cfg.configuration=@{visibleFieldIds=$visible}}
    $null=Gql $q @{input=$cfg}
    $p=(Snapshot).project
  }

  $p=(Snapshot).project
  foreach($legacy in @($p.views.nodes|Where-Object{$safeLegacy -contains $_.name})){
    if($script:ReadOnly){throw "DRIFT: safe legacy Project view remains: $($legacy.name)."}
$q=@'
mutation($input:DeleteProjectV2ViewInput!){deleteProjectV2View(input:$input){deletedViewId}}
'@
    $null=Gql $q @{input=@{viewId=$legacy.id}}
  }

  $final=(Snapshot).project
  foreach($v in $desired){
    $m=@($final.views.nodes|Where-Object{$_.name -ceq $v.name})
    if($m.Count -ne 1 -or $m[0].layout -cne $v.layout -or [string]$m[0].filter -cne [string]$v.filter){throw "VERIFY_FAIL: Project view '$($v.name)'."}
  }
  $extra=@($final.views.nodes|Where-Object{$canonical -cnotcontains $_.name})
  if($extra.Count -gt 0){throw "VERIFY_FAIL: unexpected Project views remain: $(($extra.name)-join ', ')."}
}

function Ensure-Items {
  if($script:ReadOnly){return}
  $repo="$Owner/$Repository"
  $urls=@()
  foreach($kind in @('issue','pr')){
    $raw=& gh $kind list --repo $repo --state open --limit 1000 --json url
    if($LASTEXITCODE -ne 0){throw "Cannot enumerate open $kind items."}
    if($raw){$urls+=@((($raw -join "`n")|ConvertFrom-Json)|ForEach-Object{$_.url})}
  }
  foreach($url in @($urls|Where-Object{$_}|Sort-Object -Unique)){
    $null=& gh project item-add $ProjectNumber --owner $Owner --url $url --format json 2>&1
    if($LASTEXITCODE -ne 0){throw "Cannot add Project item $url"}
  }
}

if(-not(Get-Command gh -ErrorAction SilentlyContinue)){throw 'GitHub CLI (gh) not found.'}
$null=& gh auth status 2>&1
if($LASTEXITCODE -ne 0){throw 'GitHub CLI is not authenticated.'}

Ensure-LinkAndTitle
Ensure-Select 'Статус' @('Статус','Status') @(
 (Opt 'Входящие' 'GRAY' 'Новая работа.' @('Входящие','Todo')),
 (Opt 'Нужно разобрать' 'YELLOW' 'Нужен triage.'),
 (Opt 'Готово к работе' 'BLUE' 'Задачу можно брать.'),
 (Opt 'В работе' 'ORANGE' 'Идёт активная работа.' @('В работе','In Progress')),
 (Opt 'Проверка QA' 'PURPLE' 'Независимая проверка.'),
 (Opt 'Заблокировано' 'RED' 'Есть блокер.'),
 (Opt 'Готово' 'GREEN' 'Работа завершена.' @('Готово','Done'))
)
Ensure-Select 'Этап' @('Этап','Gate') @(
 (Opt 'G0 — Порядок проекта и задач' 'GRAY' 'Project и порядок работы.'),
 (Opt 'G1 — ТЗ и базовая архитектура' 'BLUE' 'ТЗ и архитектура.'),
 (Opt 'G2 — Машинные контракты' 'PURPLE' 'Контракты.'),
 (Opt 'G3 — Основа исполняемой системы' 'ORANGE' 'Runtime foundation.'),
 (Opt 'G4 — Сквозная версия v0.1' 'GREEN' 'Первая сквозная версия.'),
 (Opt 'G5 — После v0.1' 'YELLOW' 'Дальнейшее развитие.')
)
Ensure-Select 'Приоритет' @('Приоритет','Priority') @((Opt 'P0' 'RED' 'Критично.'),(Opt 'P1' 'ORANGE' 'Важно.'),(Opt 'P2' 'YELLOW' 'Полезно.'),(Opt 'P3' 'GRAY' 'Позже.'))
Ensure-Select 'Тип' @('Тип','Work Type') @(
 (Opt 'ТЗ / архитектура' 'BLUE' 'ТЗ и архитектура.'),(Opt 'Документация' 'GRAY' 'Документация.'),(Opt 'Исследование' 'PURPLE' 'Исследование.'),(Opt 'Инфраструктура' 'ORANGE' 'Инфраструктура.'),(Opt 'Контракты' 'BLUE' 'Контракты.'),(Opt 'Исполняемая система' 'GREEN' 'Runtime.'),(Opt 'Безопасность' 'RED' 'Безопасность.'),(Opt 'Проверка качества / оценка' 'YELLOW' 'QA/Eval.')
)
Ensure-Select 'Область' @('Область') @(
 (Opt 'Архитектура и документация' 'BLUE' 'Архитектура и SSoT.'),(Opt 'Контекст и знания' 'PURPLE' 'Контекст и знания.'),(Opt 'Исполнение и исполнители' 'GREEN' 'Исполнение.'),(Opt 'Безопасность и управление' 'RED' 'Безопасность.'),(Opt 'Интерфейс и визуализация' 'YELLOW' 'UI.'),(Opt 'Инженерная инфраструктура' 'ORANGE' 'GitHub/CI/Tools.'),(Opt 'Общее / не определено' 'GRAY' 'Не классифицировано.')
)
Ensure-Select 'Размер' @('Размер') @((Opt 'XS — совсем маленькая' 'GRAY' 'XS.'),(Opt 'S — маленькая' 'BLUE' 'S.'),(Opt 'M — средняя' 'YELLOW' 'M.'),(Opt 'L — большая' 'ORANGE' 'L.'),(Opt 'XL — очень большая' 'RED' 'XL; желательно разбить.'))
$workers=@((Opt 'ChatGPT' 'GREEN' 'ChatGPT.'),(Opt 'AGY' 'BLUE' 'Антигравити.'),(Opt 'Codex' 'PURPLE' 'Codex.'),(Opt 'Человек' 'ORANGE' 'Человек.'),(Opt 'Другой' 'GRAY' 'Другой.'))
Ensure-Select 'Исполнитель' @('Исполнитель','Implementation Worker') $workers
Ensure-Select 'Проверяющий' @('Проверяющий','QA Worker') $workers
Ensure-Select 'Исполнение' @('Исполнение','Состояние работы','Claim') @((Opt 'Свободно' 'GRAY' 'Свободно.'),(Opt 'В очереди' 'BLUE' 'Ждёт следующего Gate.'),(Opt 'Активно' 'ORANGE' 'Идёт работа.'),(Opt 'На проверке' 'PURPLE' 'Передано QA.'),(Opt 'Заблокировано' 'RED' 'Блокер.'),(Opt 'Освобождено' 'GREEN' 'Работа завершена/освобождена.'))
Ensure-Select 'Цель' @('Цель','Target') @((Opt 'Базовая архитектура' 'BLUE' 'Baseline.'),(Opt 'v0.1' 'GREEN' 'v0.1.'),(Opt 'v0.2' 'PURPLE' 'v0.2.'),(Opt 'v1.0' 'ORANGE' 'v1.0.'),(Opt 'Позже' 'GRAY' 'Позже.'))
Ensure-Select 'Риск' @('Риск','Risk') @((Opt 'Критический' 'RED' 'Critical.'),(Opt 'Высокий' 'ORANGE' 'High.'),(Opt 'Средний' 'YELLOW' 'Medium.'),(Opt 'Низкий' 'GREEN' 'Low.'))
Ensure-Select 'Доказательство' @('Доказательство','Evidence') @((Opt 'Нет' 'RED' 'Evidence отсутствует.'),(Opt 'Частично' 'YELLOW' 'Evidence частичный.'),(Opt 'Автопроверки пройдены' 'BLUE' 'CI PASS.'),(Opt 'Проверка качества пройдена' 'GREEN' 'Independent QA PASS.'))
Ensure-Iteration
Ensure-Views
Ensure-Items

$final=Snapshot
[pscustomobject]@{
  schema='KAT9I_PROJECT_CONFIGURATION/1';status='PASS';owner=$Owner;repository=$Repository;project_number=$ProjectNumber;project_title=$final.project.title;items=[int]$final.project.items.totalCount;views=@($final.project.views.nodes).Count;mode=$Mode
}|ConvertTo-Json -Depth 8
