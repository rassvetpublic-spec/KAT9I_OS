[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Owner,
  [Parameter(Mandatory=$true)][string]$Repository,
  [Parameter(Mandatory=$true)][int]$ProjectNumber,
  [Parameter(Mandatory=$true)][string]$ProjectTitle,
  [string]$ViewsPolicyPath = (Join-Path $PSScriptRoot '../config/project_bootstrap_views.json'),
  [ValidateSet('Установка','Статус','Восстановление')][string]$Mode='Установка'
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Utf8NoBom=[Text.UTF8Encoding]::new($false)
$script:ReadOnly=($Mode -eq 'Статус')

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
  if($LASTEXITCODE -ne 0){throw "Ошибка GitHub CLI: gh $($Arguments -join ' ')"}
  $text=($raw -join "`n")
  if([string]::IsNullOrWhiteSpace($text)){return $null}
  return ($text|ConvertFrom-Json -Depth 50)
}

function Gql([string]$Query,[hashtable]$Variables){
  $r=Invoke-GhJson @('api','graphql') @{query=$Query;variables=$Variables}
  if($null -eq $r){throw 'GitHub GraphQL вернул пустой ответ.'}
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
  if(-not $p){throw "Project #$ProjectNumber не найден у владельца $Owner."}
  return [pscustomobject]@{project=$p;repository=$d.repository}
}

function Opt([string]$Name,[string]$Color,[string]$Description,[string[]]$Aliases=@()){
  if($Aliases.Count -eq 0){$Aliases=@($Name)}
  [pscustomobject]@{name=$Name;color=$Color;description=$Description;aliases=$Aliases}
}

function Find-Field($Fields,[string[]]$Aliases){
  $m=@(@($Fields)|Where-Object{$Aliases -contains $_.name})
  if($m.Count -gt 1){throw "Найдено несколько подходящих полей Project: $(($m.name)-join ', ')"}
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
    if($script:ReadOnly){throw "РАСХОЖДЕНИЕ: отсутствует поле Project '$Name'."}
$q=@'
mutation($input:CreateProjectV2FieldInput!){createProjectV2Field(input:$input){projectV2Field{... on ProjectV2SingleSelectField{id name}}}}
'@
    $opts=@($Defs|ForEach-Object{@{name=$_.name;color=$_.color;description=$_.description}})
    $null=Gql $q @{input=@{projectId=$p.id;name=$Name;dataType='SINGLE_SELECT';singleSelectOptions=$opts}}
    return
  }
  if($f.__typename -ne 'ProjectV2SingleSelectField'){throw "ЗАБЛОКИРОВАНО: поле '$($f.name)' имеет несовместимый тип."}
  if((Test-OptionsExact $f $Defs) -and ($f.name -ceq $Name -or ($Name -eq 'Статус' -and $f.name -eq 'Status'))){return}
  if($script:ReadOnly){throw "РАСХОЖДЕНИЕ: поле Project '$Name' отличается от стандарта."}
  if([int]$p.items.totalCount -gt 0){throw "ЗАБЛОКИРОВАНО: поле '$Name' отличается от стандарта, а в Project уже есть карточки; подготовка не будет заменять идентификаторы вариантов поля."}
  Set-SelectField $f $Name $Defs
}

function Ensure-Iteration {
  $s=Snapshot; $p=$s.project
  $f=Find-Field $p.fields.nodes @('Итерация')
  if($f){
    if($f.__typename -ne 'ProjectV2IterationField' -or [int]$f.configuration.duration -ne 3){throw 'ЗАБЛОКИРОВАНО: поле «Итерация» отличается от стандарта в 3 дня.'}
    return
  }
  if($script:ReadOnly){throw 'РАСХОЖДЕНИЕ: отсутствует поле «Итерация» длительностью 3 дня.'}
$q=@'
mutation($input:CreateProjectV2FieldInput!){createProjectV2Field(input:$input){projectV2Field{... on ProjectV2IterationField{id name}}}}
'@
  $null=Gql $q @{input=@{projectId=$p.id;name='Итерация';dataType='ITERATION';iterationConfiguration=@{startDate=(Get-Date).Date.ToString('yyyy-MM-dd');duration=3;iterations=@()}}}
}

function Ensure-LinkAndTitle {
  $s=Snapshot; $p=$s.project; $repo=$s.repository
  if(-not $repo){throw "Репозиторий $Owner/$Repository не найден."}
  if($p.title -cne $ProjectTitle){
    if($script:ReadOnly){throw "РАСХОЖДЕНИЕ: название Project '$($p.title)' не равно '$ProjectTitle'."}
$q=@'
mutation($input:UpdateProjectV2Input!){updateProjectV2(input:$input){projectV2{id title}}}
'@
    $null=Gql $q @{input=@{projectId=$p.id;title=$ProjectTitle}}
  }
  if(-not (@($p.repositories.nodes)|Where-Object{$_.id -eq $repo.id})){
    if($script:ReadOnly){throw 'РАСХОЖДЕНИЕ: Project не связан с репозиторием.'}
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
  if(-not $status){throw 'Поле «Статус» отсутствует.'}
  $desired=@($policy.views|ForEach-Object{[pscustomobject]@{name=$_.name;layout=$_.layout;filter=$_.filter.Replace('{status}',$status.name)}})
  $canonical=@($desired.name)
  $safeLegacy=@($policy.legacy_views)+@('View 1','Table')
  $unknown=@($p.views.nodes|Where-Object{$canonical -cnotcontains $_.name -and $safeLegacy -cnotcontains $_.name})
  if($unknown.Count -gt 0){throw "ЗАБЛОКИРОВАНО: найдены неизвестные представления Project: $(($unknown.name)-join ', ')."}

  $visible=@()
  foreach($alias in @('Title','Assignees','Status','Статус','Этап','Приоритет','Тип','Область','Размер','Итерация','Исполнитель','Проверяющий','Исполнение','Цель','Риск','Доказательство','Linked pull requests','Sub-issues progress')){
    $f=Find-Field $p.fields.nodes @($alias)
    if($f -and $visible -notcontains $f.id){$visible+=$f.id}
  }

  foreach($v in $desired){
    $existing=@($p.views.nodes|Where-Object{$_.name -ceq $v.name})
    if($existing.Count -gt 1){throw "ЗАБЛОКИРОВАНО: представление Project '$($v.name)' продублировано."}
    if($existing.Count -eq 1){
      if($existing[0].layout -cne $v.layout -or [string]$existing[0].filter -cne [string]$v.filter){throw "ЗАБЛОКИРОВАНО: существующее представление '$($v.name)' отличается от стандарта."}
      continue
    }
    if($script:ReadOnly){throw "РАСХОЖДЕНИЕ: отсутствует представление Project '$($v.name)'."}
$q=@'
mutation($input:CreateProjectV2ViewInput!){createProjectV2View(input:$input){projectV2View{id}}}
'@
    $createInput=@{projectId=$p.id;name=$v.name;layout=$v.layout}
    if($v.layout -ne 'ROADMAP_LAYOUT'){$createInput.configuration=@{visibleFieldIds=$visible}}
    $created=Gql $q @{input=$createInput}
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
    if($script:ReadOnly){throw "РАСХОЖДЕНИЕ: осталось устаревшее безопасно распознанное представление Project '$($legacy.name)'."}
$q=@'
mutation($input:DeleteProjectV2ViewInput!){deleteProjectV2View(input:$input){projectV2View{id}}}
'@
    $null=Gql $q @{input=@{viewId=$legacy.id}}
  }

  $final=(Snapshot).project
  foreach($v in $desired){
    $m=@($final.views.nodes|Where-Object{$_.name -ceq $v.name})
    if($m.Count -ne 1 -or $m[0].layout -cne $v.layout -or [string]$m[0].filter -cne [string]$v.filter){throw "ОШИБКА_ПРОВЕРКИ: представление Project '$($v.name)' не соответствует стандарту."}
  }
  $extra=@($final.views.nodes|Where-Object{$canonical -cnotcontains $_.name})
  if($extra.Count -gt 0){throw "ОШИБКА_ПРОВЕРКИ: после настройки остались неожиданные представления Project: $(($extra.name)-join ', ')."}
}

function Ensure-Items {
  if($script:ReadOnly){return}
  $repo="$Owner/$Repository"
  $urls=@()
  foreach($kind in @('issue','pr')){
    $raw=& gh $kind list --repo $repo --state open --limit 1000 --json url
    if($LASTEXITCODE -ne 0){throw "Не удалось получить открытые элементы типа '$kind'."}
    if($raw){
      $items=($raw -join "`n")|ConvertFrom-Json
      $urls+=@($items|ForEach-Object{$_.url})
    }
  }
  foreach($url in @($urls|Where-Object{$_}|Sort-Object -Unique)){
    $null=& gh project item-add $ProjectNumber --owner $Owner --url $url --format json 2>&1
    if($LASTEXITCODE -ne 0){throw "Не удалось добавить карточку Project: $url"}
  }
}

if(-not(Get-Command gh -ErrorAction SilentlyContinue)){throw 'GitHub CLI (gh) не найден.'}
$null=& gh auth status 2>&1
if($LASTEXITCODE -ne 0){throw 'GitHub CLI не авторизован.'}

Ensure-LinkAndTitle
Ensure-Select 'Статус' @('Статус','Status') @(
 (Opt 'Входящие' 'GRAY' 'Новая работа.' @('Входящие','Todo')),
 (Opt 'Нужно разобрать' 'YELLOW' 'Нужно определить этап, приоритет, границы работы и зависимости.'),
 (Opt 'Готово к работе' 'BLUE' 'Задачу можно брать в работу.'),
 (Opt 'В работе' 'ORANGE' 'Идёт активная работа.' @('В работе','In Progress')),
 (Opt 'Проверка качества' 'PURPLE' 'Идёт независимая проверка качества.' @('Проверка качества','Проверка QA','QA')),
 (Opt 'Заблокировано' 'RED' 'Есть блокирующее условие.'),
 (Opt 'Готово' 'GREEN' 'Работа завершена по правилам.' @('Готово','Done'))
)
Ensure-Select 'Этап' @('Этап','Gate') @(
 (Opt 'G0 — Порядок проекта и задач' 'GRAY' 'Настройка Project, очереди и порядка работы.'),
 (Opt 'G1 — ТЗ и базовая архитектура' 'BLUE' 'Техническое задание и базовая архитектура.'),
 (Opt 'G2 — Машинные контракты' 'PURPLE' 'Машинно проверяемые контракты.'),
 (Opt 'G3 — Основа исполняемой системы' 'ORANGE' 'Основа исполняемой системы.'),
 (Opt 'G4 — Сквозная версия v0.1' 'GREEN' 'Первая сквозная рабочая версия.'),
 (Opt 'G5 — После v0.1' 'YELLOW' 'Дальнейшее развитие после первой версии.')
)
Ensure-Select 'Приоритет' @('Приоритет','Priority') @((Opt 'P0' 'RED' 'Критично.'),(Opt 'P1' 'ORANGE' 'Важно.'),(Opt 'P2' 'YELLOW' 'Полезно.'),(Opt 'P3' 'GRAY' 'Позже.'))
Ensure-Select 'Тип' @('Тип','Work Type') @(
 (Opt 'ТЗ / архитектура' 'BLUE' 'Техническое задание и архитектура.'),(Opt 'Документация' 'GRAY' 'Документация.'),(Opt 'Исследование' 'PURPLE' 'Исследование.'),(Opt 'Инфраструктура' 'ORANGE' 'Инфраструктура.'),(Opt 'Контракты' 'BLUE' 'Машинные контракты.'),(Opt 'Исполняемая система' 'GREEN' 'Исполняемый код и службы.'),(Opt 'Безопасность' 'RED' 'Безопасность.'),(Opt 'Проверка качества / оценка' 'YELLOW' 'Проверка качества и оценка.')
)
Ensure-Select 'Область' @('Область') @(
 (Opt 'Архитектура и документация' 'BLUE' 'Архитектура, документация и единый источник истины.'),(Opt 'Контекст и знания' 'PURPLE' 'Контекст, память и знания.'),(Opt 'Исполнение и исполнители' 'GREEN' 'Исполнение задач и исполнители.'),(Opt 'Безопасность и управление' 'RED' 'Безопасность и правила управления.'),(Opt 'Интерфейс и визуализация' 'YELLOW' 'Интерфейс и отображение информации.'),(Opt 'Инженерная инфраструктура' 'ORANGE' 'GitHub, автоматические проверки и инструменты.'),(Opt 'Общее / не определено' 'GRAY' 'Ещё не классифицировано.')
)
Ensure-Select 'Размер' @('Размер') @((Opt 'XS — совсем маленькая' 'GRAY' 'Совсем маленькая задача.'),(Opt 'S — маленькая' 'BLUE' 'Маленькая задача.'),(Opt 'M — средняя' 'YELLOW' 'Средняя задача.'),(Opt 'L — большая' 'ORANGE' 'Большая задача.'),(Opt 'XL — очень большая' 'RED' 'Очень большая задача; желательно разбить на более мелкие.'))
$workers=@((Opt 'ChatGPT' 'GREEN' 'ChatGPT.'),(Opt 'Антигравити' 'BLUE' 'Антигравити.' @('Антигравити','AGY')),(Opt 'Codex' 'PURPLE' 'Codex.'),(Opt 'Человек' 'ORANGE' 'Человек.'),(Opt 'Другой' 'GRAY' 'Другой исполнитель.'))
Ensure-Select 'Исполнитель' @('Исполнитель','Implementation Worker') $workers
Ensure-Select 'Проверяющий' @('Проверяющий','QA Worker') $workers
Ensure-Select 'Исполнение' @('Исполнение','Состояние работы','Claim') @((Opt 'Свободно' 'GRAY' 'Никто не взял работу.'),(Opt 'В очереди' 'BLUE' 'Работа ждёт следующего разрешённого шага.'),(Opt 'Активно' 'ORANGE' 'Исполнитель прямо сейчас работает над задачей.'),(Opt 'На проверке' 'PURPLE' 'Работа передана независимому проверяющему.'),(Opt 'Заблокировано' 'RED' 'Продолжение работы заблокировано.'),(Opt 'Освобождено' 'GREEN' 'Исполнитель освободил задачу после завершения.'))
Ensure-Select 'Цель' @('Цель','Target') @((Opt 'Базовая архитектура' 'BLUE' 'Принятая базовая архитектура.'),(Opt 'v0.1' 'GREEN' 'Первая рабочая версия.'),(Opt 'v0.2' 'PURPLE' 'Следующая рабочая версия.'),(Opt 'v1.0' 'ORANGE' 'Первая стабильная версия.'),(Opt 'Позже' 'GRAY' 'Не входит в ближайшие версии.'))
Ensure-Select 'Риск' @('Риск','Risk') @((Opt 'Критический' 'RED' 'Критический риск.'),(Opt 'Высокий' 'ORANGE' 'Высокий риск.'),(Opt 'Средний' 'YELLOW' 'Средний риск.'),(Opt 'Низкий' 'GREEN' 'Низкий риск.'))
Ensure-Select 'Доказательство' @('Доказательство','Evidence') @((Opt 'Нет' 'RED' 'Подтверждения результата пока нет.'),(Opt 'Частично' 'YELLOW' 'Есть только часть подтверждений.'),(Opt 'Автопроверки пройдены' 'BLUE' 'Автоматические проверки пройдены на точной версии.'),(Opt 'Проверка качества пройдена' 'GREEN' 'Независимая проверка качества пройдена на точной версии.'))
Ensure-Iteration
Ensure-Views
Ensure-Items

$final=Snapshot
[pscustomobject]@{
  schema='KAT9I_PROJECT_CONFIGURATION/1';status='ПРОЙДЕНО';owner=$Owner;repository=$Repository;project_number=$ProjectNumber;project_title=$final.project.title;items=[int]$final.project.items.totalCount;views=@($final.project.views.nodes).Count;mode=$Mode
}|ConvertTo-Json -Depth 8