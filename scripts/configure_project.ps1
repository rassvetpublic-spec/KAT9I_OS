param(
  [string]$Owner='rassvetpublic-spec',
  [string]$Repository='KAT9I_OS',
  [int]$ProjectNumber=2,
  [switch]$LibraryMode
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ApiVersion='2026-03-10'
$script:ProjectPreflightOnly=$false

$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $Utf8NoBom
[Console]::OutputEncoding = $Utf8NoBom
$global:OutputEncoding = $Utf8NoBom
try {
  [System.Text.Encoding]::RegisterProvider([System.Text.CodePagesEncodingProvider]::Instance)
} catch {}

function Invoke-GhJson {
  param(
    [Parameter(Mandatory=$true)][string[]]$Arguments,
    [Parameter(Mandatory=$true)]$Payload
  )
  $tmp=[System.IO.Path]::GetTempFileName()
  try {
    $json=$Payload | ConvertTo-Json -Depth 40 -Compress
    [System.IO.File]::WriteAllText($tmp,$json,$Utf8NoBom)
    $raw=& gh @Arguments --input $tmp
    if($LASTEXITCODE -ne 0){throw "GitHub CLI завершился с ошибкой: gh $($Arguments -join ' ')"}
    if([string]::IsNullOrWhiteSpace(($raw -join "`n"))){return $null}
    return (($raw -join "`n") | ConvertFrom-Json -Depth 40)
  }
  finally {
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
  }
}

function Gql([string]$Query,[hashtable]$Variables){
  $r=Invoke-GhJson -Arguments @('api','graphql') -Payload @{query=$Query;variables=$Variables}
  if($null -eq $r){throw 'GitHub GraphQL API вернул пустой ответ.'}
  $errorsProperty=$r.PSObject.Properties['errors']
  if($null -ne $errorsProperty -and $null -ne $errorsProperty.Value){
    $messages=@($errorsProperty.Value|ForEach-Object{
      $messageProperty=$_.PSObject.Properties['message']
      if($null -ne $messageProperty){$messageProperty.Value}else{$_|ConvertTo-Json -Depth 10 -Compress}
    })
    throw ($messages -join '; ')
  }
  return $r
}

function Rest([string]$Endpoint,[string]$Method='GET',$Body=$null){
  if($null -eq $Body){
    $raw=& gh api --method $Method -H 'Accept: application/vnd.github+json' -H "X-GitHub-Api-Version: $ApiVersion" $Endpoint
    if($LASTEXITCODE -ne 0){throw "GitHub REST API вернул ошибку: $Endpoint"}
    if([string]::IsNullOrWhiteSpace(($raw -join "`n"))){return $null}
    return (($raw -join "`n")|ConvertFrom-Json -Depth 40)
  }
  return Invoke-GhJson -Arguments @('api','--method',$Method,'-H','Accept: application/vnd.github+json','-H',"X-GitHub-Api-Version: $ApiVersion",$Endpoint) -Payload $Body
}

function Legacy-Oem866([string]$Text){
  if([string]::IsNullOrEmpty($Text)){return $Text}
  try {
    return [System.Text.Encoding]::GetEncoding(866).GetString([System.Text.Encoding]::UTF8.GetBytes($Text))
  } catch {
    return $Text
  }
}

function Expand-Aliases([string[]]$Aliases){
  $out=New-Object System.Collections.Generic.List[string]
  foreach($a in $Aliases){
    if([string]::IsNullOrWhiteSpace($a)){continue}
    if(-not $out.Contains($a)){$out.Add($a)}
    $bad=Legacy-Oem866 $a
    if(-not $out.Contains($bad)){$out.Add($bad)}
    $bad2=Legacy-Oem866 $bad
    if(-not $out.Contains($bad2)){$out.Add($bad2)}
  }
  return @($out)
}

function Is-Alias([string]$Value,[string[]]$Aliases){
  return (Expand-Aliases $Aliases) -contains $Value
}

function Snapshot{
$q=@'
query($login:String!,$number:Int!,$repo:String!){
 user(login:$login){
   id
   projectV2(number:$number){
     id title url
     repositories(first:100){nodes{id nameWithOwner}}
     fields(first:100){
       nodes{
         __typename
         ... on ProjectV2Field{id name dataType}
         ... on ProjectV2SingleSelectField{id name dataType options{id name color description}}
         ... on ProjectV2IterationField{id name dataType configuration{duration startDay}}
       }
     }
     views(first:100){nodes{id name layout filter}}
   }
 }
 repository(owner:$login,name:$repo){id nameWithOwner}
}
'@
  return (Gql $q @{login=$Owner;number=$ProjectNumber;repo=$Repository}).data
}

function Opt([string]$Name,[string]$Color,[string]$Description,[string[]]$Aliases=@()){
  if($Aliases.Count -eq 0){$Aliases=@($Name)}
  [ordered]@{name=$Name;color=$Color;description=$Description;aliases=$Aliases}
}

function Find-Field($Fields,[string[]]$Aliases){
  $matches=@(@($Fields)|Where-Object{Is-Alias $_.name $Aliases})
  if($matches.Count -gt 1){
    throw "Найдены неоднозначные поля Project для '$($Aliases[0])': $(($matches.name)-join ', '). Скрипт остановлен без изменений."
  }
  if($matches.Count -eq 1){return $matches[0]}
  return $null
}

function EnsureSelect([string]$Name,[string[]]$FieldAliases,[object[]]$Defs){
  if($FieldAliases.Count -eq 0){$FieldAliases=@($Name)}
  $aliases=@($FieldAliases + $Name | Select-Object -Unique)
  $p=(Snapshot).user.projectV2
  $f=Find-Field $p.fields.nodes $aliases

  if(-not $f){
    if($script:ProjectPreflightOnly){return}
$q=@'
mutation($input:CreateProjectV2FieldInput!){
 createProjectV2Field(input:$input){
   projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}
 }
}
'@
    $opts=@($Defs|ForEach-Object{[ordered]@{name=$_.name;color=$_.color;description=$_.description}})
    $null=Gql $q @{input=@{projectId=$p.id;name=$Name;dataType='SINGLE_SELECT';singleSelectOptions=$opts}}
    Write-Host "Создано поле: $Name"
    return
  }

  if($f.__typename -ne 'ProjectV2SingleSelectField'){throw "Поле '$($f.name)' уже существует с другим типом."}

  $unknown=@()
  foreach($existing in @($f.options)){
    $matched=$false
    foreach($d in $Defs){
      if(Is-Alias $existing.name @($d.aliases + $d.name)){
        $matched=$true
        break
      }
    }
    if(-not $matched){$unknown+=$existing}
  }
  if($unknown.Count -gt 0){
    throw "Поле '$($f.name)' содержит действительно неизвестные значения: $(($unknown.name)-join ', '). Скрипт ничего не удалил."
  }

  $missing=@()
  $legacy=@()
  foreach($d in $Defs){
    $matches=@(@($f.options)|Where-Object{Is-Alias $_.name @($d.aliases + $d.name)})
    if($matches.Count -gt 1){
      throw "Поле '$($f.name)' содержит неоднозначные значения для '$($d.name)': $(($matches.name)-join ', '). Скрипт остановлен без изменений."
    }
    if($matches.Count -eq 0){
      $missing+=$d.name
    } elseif($matches[0].name -cne $d.name){
      $existing=$matches[0]
      $legacy+="$($existing.name) -> $($d.name)"
    }
  }

  if($missing.Count -gt 0 -or $legacy.Count -gt 0){
    $details=@()
    if($missing.Count -gt 0){$details+="отсутствуют: $(($missing)-join ', ')"}
    if($legacy.Count -gt 0){$details+="нужна миграция значений: $(($legacy)-join ', ')"}
    throw "Поле '$($f.name)' требует изменения option ID ($($details -join '; ')). GitHub API не позволяет доказуемо сохранить привязки Items при таком переименовании, поэтому скрипт остановлен без изменения значений. Выполните явную миграцию данных и повторите запуск."
  }

  if($f.name -cne $Name -and $Name -eq 'Статус' -and $f.name -eq 'Status'){
    Write-Host 'Проверено встроенное поле Status: системное имя GitHub неизменно; значения отображаются по-русски.'
  } elseif($f.name -cne $Name){
$q=@'
mutation($input:UpdateProjectV2FieldInput!){
 updateProjectV2Field(input:$input){
   projectV2Field{... on ProjectV2SingleSelectField{id name}}
 }
}
'@
    $oldName=$f.name
    $null=Gql $q @{input=@{fieldId=$f.id;name=$Name}}
    Write-Host "Исправлено имя поля без изменения option ID: $oldName -> $Name"
  } else {
    Write-Host "Проверено поле: $Name"
  }
}

function Start-Date3Days{
  return (Get-Date).Date.ToString('yyyy-MM-dd')
}

function EnsureIteration{
  $p=(Snapshot).user.projectV2
  $f=Find-Field $p.fields.nodes @('Итерация')
  if($f){
    if($f.__typename -ne 'ProjectV2IterationField'){throw "Поле '$($f.name)' существует с другим типом."}
    if($f.name -cne 'Итерация'){
      throw "Поле Итерация имеет неканоническое имя '$($f.name)'. Безопасная миграция существующих периодов не доказана; изменение остановлено."
    }
    if([int]$f.configuration.duration -ne 3){
      throw "Поле Итерация уже существует с длительностью $($f.configuration.duration) дней. Настройщик не сбрасывает существующие периоды и привязки Items; выполните явную безопасную миграцию к 3 дням и повторите запуск."
    }
    Write-Host 'Проверено поле: Итерация (3 дня)'
    return
  }
  if($script:ProjectPreflightOnly){return}

$q=@'
mutation($input:CreateProjectV2FieldInput!){
 createProjectV2Field(input:$input){
   projectV2Field{... on ProjectV2IterationField{id name}}
 }
}
'@
  $null=Gql $q @{input=@{projectId=$p.id;name='Итерация';dataType='ITERATION';iterationConfiguration=@{startDate=(Start-Date3Days);duration=3;iterations=@()}}}
  Write-Host 'Создано поле Итерация: 3 дня'
}

function EnsureLink{
  $s=Snapshot
  $p=$s.user.projectV2
  $repo=$s.repository
  if(-not $p){throw "Project #$ProjectNumber не найден."}

  if($p.title -ne 'KAT9I_OS — разработка'){
    if($script:ProjectPreflightOnly){return}
$q=@'
mutation($input:UpdateProjectV2Input!){
 updateProjectV2(input:$input){projectV2{id title}}
}
'@
    $null=Gql $q @{input=@{projectId=$p.id;title='KAT9I_OS — разработка'}}
    Write-Host 'Исправлено название Project.'
  }

  if(-not (@($p.repositories.nodes)|Where-Object{$_.id -eq $repo.id})){
    if($script:ProjectPreflightOnly){return}
$q=@'
mutation($input:LinkProjectV2ToRepositoryInput!){
 linkProjectV2ToRepository(input:$input){repository{id}}
}
'@
    $null=Gql $q @{input=@{projectId=$p.id;repositoryId=$repo.id}}
    Write-Host 'Project связан с репозиторием.'
  }
}

function EnsureItems{
  if($script:ProjectPreflightOnly){return}
  $repo="$Owner/$Repository"
  $urls=@()

  $j=& gh issue list --repo $repo --state open --limit 1000 --json url
  if($LASTEXITCODE -ne 0){throw 'Не удалось получить полный список открытых Issues. Project не изменён дальше.'}
  if($j){$urls+=@((($j -join "`n")|ConvertFrom-Json).url)}

  $j=& gh pr list --repo $repo --state open --limit 1000 --json url
  if($LASTEXITCODE -ne 0){throw 'Не удалось получить полный список открытых PR. Project не изменён дальше.'}
  if($j){$urls+=@((($j -join "`n")|ConvertFrom-Json).url)}

  $urls+="https://github.com/$repo/issues/62"

  foreach($u in @($urls|Sort-Object -Unique)){
    $null=& gh project item-add $ProjectNumber --owner $Owner --url $u --format json 2>&1
    if($LASTEXITCODE -ne 0){throw "Не удалось добавить $u"}
  }
  Write-Host 'Актуальные открытые Issues/PR и управляющая Issue #62 добавлены.'
}

function FieldMapViaGraphQL{
  $p=(Snapshot).user.projectV2
  $m=@{}
  foreach($f in @($p.fields.nodes)){
    $m[$f.name]=$f
  }
  return $m
}

function Find-MapField($Map,[string[]]$Aliases){
  foreach($key in @($Map.Keys)){
    if(Is-Alias $key $Aliases){return $Map[$key]}
  }
  return $null
}

function PreflightViews{
  $project=(Snapshot).user.projectV2
  $statusField=Find-Field $project.fields.nodes @('Статус','Status')
  $statusName=if($statusField){$statusField.name}else{'Статус'}
  $views=@(
    @{n='00 — Все задачи';gl='TABLE_LAYOUT';f='is:open'},
    @{n='01 — Готово к работе';gl='TABLE_LAYOUT';f="is:open ${statusName}:`"Готово к работе`" -Исполнение:`"Заблокировано`""},
    @{n='02 — В работе';gl='BOARD_LAYOUT';f="is:open ${statusName}:`"В работе`""},
    @{n='03 — Проверка';gl='BOARD_LAYOUT';f="is:open ${statusName}:`"Проверка QA`""},
    @{n='04 — Заблокировано';gl='TABLE_LAYOUT';f="is:open ${statusName}:`"Заблокировано`""}
  )
  $canonicalNames=@($views|ForEach-Object{$_.n})
  $legacyViewNames=@(
    '00 — Центр управления',
    '01 — Архитектура G1',
    '02 — Готово к работе',
    '03 — Активные исполнители',
    '04 — Очередь проверки',
    '05 — Заблокировано',
    '06 — План v0.1',
    '07 — Безопасность',
    '08 — Доказательства',
    '09 — Без классификации'
  )
  $knownNames=@($canonicalNames + $legacyViewNames)
  $initialViews=@((Snapshot).user.projectV2.views.nodes)

  $unexpected=@($initialViews|Where-Object{$knownNames -cnotcontains $_.name})
  if($unexpected.Count -gt 0){
    throw "Project содержит неизвестные или регистрово отличающиеся представления: $(($unexpected.name)-join ', '). Preflight остановлен до любых изменений."
  }

  foreach($name in @($knownNames|Select-Object -Unique)){
    $matches=@($initialViews|Where-Object{$_.name -ceq $name})
    if($matches.Count -gt 1){
      throw "Project содержит дубли представления '$name'. Preflight остановлен до любых изменений."
    }
  }

  foreach($v in $views){
    $matches=@($initialViews|Where-Object{$_.name -ceq $v['n']})
    if($matches.Count -eq 1){
      $existing=$matches[0]
      if($existing.layout -cne $v['gl'] -or [string]$existing.filter -cne [string]$v['f']){
        throw "Представление '$($v['n'])' нарушает контракт: ожидаются layout=$($v['gl']) и filter='$($v['f'])', фактически layout=$($existing.layout) и filter='$($existing.filter)'. Preflight остановлен до любых изменений."
      }
    }
  }

  return $initialViews
}

function Invoke-ProjectConfiguration([scriptblock]$Apply){
  $null=PreflightViews
  $script:ProjectPreflightOnly=$true
  try { & $Apply } finally { $script:ProjectPreflightOnly=$false }
  & $Apply
}

function EnsureViews{
  if($script:ProjectPreflightOnly){return}
  $required=@('Этап','Приоритет','Область','Исполнитель','Проверяющий','Исполнение')
  $m=$null
  for($attempt=1;$attempt -le 10;$attempt++){
    $m=FieldMapViaGraphQL
    $missing=@()
    foreach($n in $required){
      if(-not (Find-MapField $m @($n))){$missing+=$n}
    }
    if($missing.Count -eq 0){break}
    if($attempt -lt 10){
      Write-Host "GitHub ещё синхронизирует поля. Повтор $attempt/10..."
      Start-Sleep -Seconds 2
    }
  }

  $missing=@()
  foreach($n in $required){
    if(-not (Find-MapField $m @($n))){$missing+=$n}
  }
  if($missing.Count -gt 0){throw "После ожидания API не видит поля: $(($missing)-join ', ')."}

  $status=Find-MapField $m @('Статус','Status')
  if(-not $status){throw 'Project не содержит системное поле Status/Статус.'}
  $statusName=$status.name
  $id=@{'Статус'=$status.id}
  foreach($n in $required){$id[$n]=(Find-MapField $m @($n)).id}
  $vid=@()
  foreach($aliases in @(@('Title'),@('Assignees'),@('Статус','Status'),@('Этап'),@('Приоритет'),@('Область'),@('Тип'),@('Размер'),@('Итерация'),@('Исполнитель'),@('Проверяющий'),@('Исполнение'),@('Цель'),@('Риск'),@('Доказательство'),@('Linked pull requests'),@('Sub-issues progress'))){
    $field=Find-MapField $m $aliases
    if($field){$vid+=$field.id}
  }

  $views=@(
    @{n='00 — Все задачи';l='table';gl='TABLE_LAYOUT';f='is:open';s=@(@($id['Этап'],'asc'),@($id['Приоритет'],'asc'),@($id['Статус'],'asc'))},
    @{n='01 — Готово к работе';l='TABLE_LAYOUT';gl='TABLE_LAYOUT';f="is:open ${statusName}:`"Готово к работе`" -Исполнение:`"Заблокировано`""},
    @{n='02 — В работе';l='BOARD_LAYOUT';gl='BOARD_LAYOUT';f="is:open ${statusName}:`"В работе`""},
    @{n='03 — Проверка';l='BOARD_LAYOUT';gl='BOARD_LAYOUT';f="is:open ${statusName}:`"Проверка QA`""},
    @{n='04 — Заблокировано';l='TABLE_LAYOUT';gl='TABLE_LAYOUT';f="is:open ${statusName}:`"Заблокировано`""}
  )

  $canonicalNames=@($views|ForEach-Object{$_.n})
  $legacyViewNames=@(
    '00 — Центр управления',
    '01 — Архитектура G1',
    '02 — Готово к работе',
    '03 — Активные исполнители',
    '04 — Очередь проверки',
    '05 — Заблокировано',
    '06 — План v0.1',
    '07 — Безопасность',
    '08 — Доказательства',
    '09 — Без классификации'
  )
  $knownNames=@($canonicalNames + $legacyViewNames)

  $initialViews=@((Snapshot).user.projectV2.views.nodes)
  $unexpected=@($initialViews|Where-Object{$knownNames -cnotcontains $_.name})
  if($unexpected.Count -gt 0){
    throw "Project содержит неизвестные или регистрово отличающиеся представления: $(($unexpected.name)-join ', '). Preflight остановлен до любых изменений."
  }

  foreach($name in @($knownNames|Select-Object -Unique)){
    $matches=@($initialViews|Where-Object{$_.name -ceq $name})
    if($matches.Count -gt 1){
      throw "Project содержит дубли представления '$name'. Preflight остановлен до любых изменений."
    }
  }

  foreach($v in $views){
    $matches=@($initialViews|Where-Object{$_.name -ceq $v['n']})
    if($matches.Count -eq 1){
      $existing=$matches[0]
      if($existing.layout -cne $v['gl'] -or [string]$existing.filter -cne [string]$v['f']){
        throw "Представление '$($v['n'])' нарушает контракт: ожидаются layout=$($v['gl']) и filter='$($v['f'])', фактически layout=$($existing.layout) и filter='$($existing.filter)'. Preflight остановлен до любых изменений."
      }
    }
  }

  foreach($v in $views){
    $matches=@($initialViews|Where-Object{$_.name -ceq $v['n']})
    if($matches.Count -eq 1){continue}

    $q='mutation($input:CreateProjectV2ViewInput!){createProjectV2View(input:$input){projectV2View{id}}}'
    $created=Gql $q @{input=@{projectId=$p.id;name=$v['n'];layout=$v['l'];configuration=@{visibleFieldIds=$vid}}}
    $viewId=$created.data.createProjectV2View.projectV2View.id
    $q='mutation($input:UpdateProjectV2ViewInput!){updateProjectV2View(input:$input){projectV2View{id}}}'
    $null=Gql $q @{input=@{viewId=$viewId;filter=$v['f'];configuration=@{visibleFieldIds=$vid}}}
    Write-Host "Создано представление: $($v['n'])"
  }

  $afterCreate=@((Snapshot).user.projectV2.views.nodes)
  foreach($v in $views){
    $matches=@($afterCreate|Where-Object{$_.name -ceq $v['n']})
    if($matches.Count -ne 1){
      throw "После создания представление '$($v['n'])' существует неоднозначно: экземпляров $($matches.Count). Старые представления не удалены."
    }
    $existing=$matches[0]
    if($existing.layout -cne $v['gl'] -or [string]$existing.filter -cne [string]$v['f']){
      throw "После создания представление '$($v['n'])' не соответствует контракту. Старые представления не удалены."
    }
  }

  foreach($legacy in @($afterCreate|Where-Object{$legacyViewNames -ccontains $_.name})){
$q=@'
mutation($input:DeleteProjectV2ViewInput!){
 deleteProjectV2View(input:$input){projectV2View{id}}
}
'@
    $null=Gql $q @{input=@{viewId=$legacy.id}}
    Write-Host "Удалено устаревшее представление: $($legacy.name)"
  }

  $finalViews=@((Snapshot).user.projectV2.views.nodes)
  if($finalViews.Count -ne 5){
    throw "После очистки Project содержит $($finalViews.Count) представлений вместо 5. Автоматическая коррекция остановлена."
  }

  foreach($v in $views){
    $matches=@($finalViews|Where-Object{$_.name -ceq $v['n']})
    if($matches.Count -ne 1){throw "Каноническое представление '$($v['n'])' должно существовать ровно в одном экземпляре."}
    $existing=$matches[0]
    if($existing.layout -cne $v['gl'] -or [string]$existing.filter -cne [string]$v['f']){
      throw "Каноническое представление '$($v['n'])' не соответствует контракту layout/filter."
    }
  }

  $unexpected=@($finalViews|Where-Object{$canonicalNames -cnotcontains $_.name})
  if($unexpected.Count -gt 0){
    throw "Project содержит неизвестные дополнительные представления: $(($unexpected.name)-join ', '). Они не удалены автоматически; требуется ручной разбор."
  }

  Write-Host 'Проверено: в Project ровно 5 канонических рабочих представлений; имя, layout и filter соответствуют контракту.'
}

if($LibraryMode){return}

if(-not(Get-Command gh -ErrorAction SilentlyContinue)){throw 'GitHub CLI (gh) не найден.'}
$null=& gh auth status 2>&1
if($LASTEXITCODE -ne 0){throw 'GitHub CLI не авторизован.'}
$null=& gh project view $ProjectNumber --owner $Owner --format json 2>&1
if($LASTEXITCODE -ne 0){throw 'Нужен scope project. Авторизуйте GitHub CLI с разрешением project.'}

Invoke-ProjectConfiguration {
EnsureLink

EnsureSelect 'Статус' @('Статус','Status') @(
 (Opt 'Входящие' 'GRAY' 'Новая работа.' @('Входящие','Todo')),
 (Opt 'Нужно разобрать' 'YELLOW' 'Нужно определить этап, приоритет, границы работы и зависимости.' @('Нужно разобрать','Разбор')),
 (Opt 'Готово к работе' 'BLUE' 'Задачу можно брать.'),
 (Opt 'В работе' 'ORANGE' 'Идёт активная работа.' @('В работе','In Progress')),
 (Opt 'Проверка QA' 'PURPLE' 'Результат проходит review / независимую проверку качества.' @('Проверка QA','Проверка качества','QA')),
 (Opt 'Заблокировано' 'RED' 'Есть блокер.' @('Заблокировано','Blocked')),
 (Opt 'Готово' 'GREEN' 'Работа завершена по правилам.' @('Готово','Done'))
)

EnsureSelect 'Этап' @('Этап','Gate') @(
 (Opt 'G0 — Порядок проекта и задач' 'GRAY' 'Project, backlog и порядок задач.' @('G0 — Порядок проекта и задач','G0 — Project/Backlog Hygiene','G0')),
 (Opt 'G1 — ТЗ и базовая архитектура' 'BLUE' 'ТЗ и базовая архитектура.' @('G1 — ТЗ и базовая архитектура','G1 — ТЗ и Architecture Baseline','G1')),
 (Opt 'G2 — Машинные контракты' 'PURPLE' 'Машинные контракты.' @('G2 — Машинные контракты','G2 — Machine Contracts','G2')),
 (Opt 'G3 — Основа исполняемой системы' 'ORANGE' 'Основа исполняемой системы.' @('G3 — Основа исполняемой системы','G3 — Runtime Foundation','G3')),
 (Opt 'G4 — Сквозная версия v0.1' 'GREEN' 'Первая сквозная версия.' @('G4 — Сквозная версия v0.1','G4 — Vertical v0.1','G4')),
 (Opt 'G5 — После v0.1' 'YELLOW' 'Работы после v0.1.' @('G5 — После v0.1','G5 — после v0.1','G5'))
)

EnsureSelect 'Приоритет' @('Приоритет','Priority') @(
 (Opt 'P0' 'RED' 'Критично.'),
 (Opt 'P1' 'ORANGE' 'Важно.'),
 (Opt 'P2' 'YELLOW' 'Полезно.'),
 (Opt 'P3' 'GRAY' 'Позже.')
)

EnsureSelect 'Тип' @('Тип','Work Type') @(
 (Opt 'ТЗ / архитектура' 'BLUE' 'ТЗ и архитектура.' @('ТЗ / архитектура','ТЗ/Architecture')),
 (Opt 'Документация' 'GRAY' 'Документация.' @('Документация','Documentation')),
 (Opt 'Исследование' 'PURPLE' 'Исследование.' @('Исследование','Research')),
 (Opt 'Инфраструктура' 'ORANGE' 'Инфраструктура.' @('Инфраструктура','Infrastructure')),
 (Opt 'Контракты' 'BLUE' 'Контракты.' @('Контракты','Contract')),
 (Opt 'Исполняемая система' 'GREEN' 'Исполняемый Runtime.' @('Исполняемая система','Runtime')),
 (Opt 'Безопасность' 'RED' 'Безопасность.' @('Безопасность','Security')),
 (Opt 'Проверка качества / оценка' 'YELLOW' 'Проверка качества и оценка.' @('Проверка качества / оценка','QA/Eval'))
)

EnsureSelect 'Область' @('Область') @(
 (Opt 'Архитектура и документация' 'BLUE' 'Архитектура и единый источник истины.'),
 (Opt 'Контекст и знания' 'PURPLE' 'Контекст, память и знания.'),
 (Opt 'Исполнение и исполнители' 'GREEN' 'Исполнение задач и исполнители.' @('Исполнение и исполнители','Исполнение и Workers')),
 (Opt 'Безопасность и управление' 'RED' 'Безопасность и правила управления.'),
 (Opt 'Интерфейс и визуализация' 'YELLOW' 'Интерфейс и отображение информации.'),
 (Opt 'Инженерная инфраструктура' 'ORANGE' 'GitHub, автопроверки и инструменты.'),
 (Opt 'Общее / не определено' 'GRAY' 'Ещё не классифицировано.')
)

EnsureSelect 'Размер' @('Размер') @(
 (Opt 'XS — совсем маленькая' 'GRAY' 'Совсем маленькая.' @('XS — совсем маленькая','XS')),
 (Opt 'S — маленькая' 'BLUE' 'Маленькая.' @('S — маленькая','S')),
 (Opt 'M — средняя' 'YELLOW' 'Средняя.' @('M — средняя','M')),
 (Opt 'L — большая' 'ORANGE' 'Большая.' @('L — большая','L')),
 (Opt 'XL — очень большая' 'RED' 'Нужно разбить на более мелкие задачи.' @('XL — очень большая','XL'))
)

$workers=@(
 (Opt 'ChatGPT' 'GREEN' 'ChatGPT.'),
 (Opt 'AGY' 'BLUE' 'AGY.'),
 (Opt 'Codex' 'PURPLE' 'Codex.'),
 (Opt 'Человек' 'ORANGE' 'Человек.' @('Человек','Human')),
 (Opt 'Другой' 'GRAY' 'Другой исполнитель.' @('Другой','Other'))
)
EnsureSelect 'Исполнитель' @('Исполнитель','Implementation Worker') $workers
EnsureSelect 'Проверяющий' @('Проверяющий','QA Worker') $workers

EnsureSelect 'Исполнение' @('Исполнение','Состояние работы','Claim') @(
 (Opt 'Свободно' 'GRAY' 'Никто не взял работу.' @('Свободно','UNCLAIMED')),
 (Opt 'В очереди' 'BLUE' 'Работа зарезервирована.' @('В очереди','QUEUED')),
 (Opt 'Активно' 'ORANGE' 'Исполнитель прямо сейчас работает над задачей.' @('Активно','ACTIVE')),
 (Opt 'На проверке' 'PURPLE' 'Работа передана отдельному проверяющему.' @('На проверке','QA')),
 (Opt 'Заблокировано' 'RED' 'Продолжение работы заблокировано.' @('Заблокировано','BLOCKED')),
 (Opt 'Освобождено' 'GREEN' 'Исполнитель освободил задачу после завершения.' @('Освобождено','RELEASED'))
)

EnsureSelect 'Цель' @('Цель','Target') @(
 (Opt 'Базовая архитектура' 'BLUE' 'Базовая принятая архитектура.' @('Базовая архитектура','Architecture Baseline')),
 (Opt 'v0.1' 'GREEN' 'Первая рабочая версия.'),
 (Opt 'v0.2' 'PURPLE' 'Следующая версия.'),
 (Opt 'v1.0' 'ORANGE' 'Первая стабильная версия.'),
 (Opt 'Позже' 'GRAY' 'Не входит в ближайшие версии.' @('Позже','Later'))
)

EnsureSelect 'Риск' @('Риск','Risk') @(
 (Opt 'Критический' 'RED' 'Критический риск.' @('Критический','Critical')),
 (Opt 'Высокий' 'ORANGE' 'Высокий риск.' @('Высокий','High')),
 (Opt 'Средний' 'YELLOW' 'Средний риск.' @('Средний','Medium')),
 (Opt 'Низкий' 'GREEN' 'Низкий риск.' @('Низкий','Low'))
)

EnsureSelect 'Доказательство' @('Доказательство','Evidence') @(
 (Opt 'Нет' 'RED' 'Подтверждения результата пока нет.' @('Нет','Missing')),
 (Opt 'Частично' 'YELLOW' 'Есть только часть подтверждений.' @('Частично','Partial')),
 (Opt 'Автопроверки пройдены' 'BLUE' 'Автоматические проверки пройдены на точной версии.' @('Автопроверки пройдены','CI PASS')),
 (Opt 'Проверка качества пройдена' 'GREEN' 'Независимая проверка качества пройдена на точной версии.' @('Проверка качества пройдена','QA PASS'))
)

EnsureIteration
EnsureItems
EnsureViews
}

Write-Host ''
Write-Host 'Готово: Project #2 приведён к русской схеме, итерация = 3 дня, рабочих представлений = 5.'
Write-Host 'Слияние, прохождение проверки качества и прохождение этапа автоматически не выполняются.'
