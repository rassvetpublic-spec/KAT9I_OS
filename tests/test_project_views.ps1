Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$scriptPath=Join-Path $PSScriptRoot '..' 'scripts' 'configure_project.ps1'
. $scriptPath -LibraryMode

function Start-Sleep { param([int]$Seconds) }

$script:Required=@('Статус','Этап','Приоритет','Область','Исполнитель','Проверяющий','Исполнение')
$script:MockViews=@()
$script:GqlCalls=0
$script:RestWrites=0
$script:ItemAddCalls=0
$script:IterationMode=$false
$script:IterationDuration=3
$script:CustomFields=$null

function New-View([string]$Name,[string]$Id,[string]$Layout,[string]$Filter){
  [pscustomobject]@{id=$Id;name=$Name;layout=$Layout;filter=$Filter}
}

function New-CanonicalViews {
  @(
    (New-View '00 — Все задачи' 'C0' 'TABLE_LAYOUT' 'is:open'),
    (New-View '01 — Готово к работе' 'C1' 'TABLE_LAYOUT' 'is:open Статус:"Готово к работе" -Исполнение:"Заблокировано"'),
    (New-View '02 — В работе' 'C2' 'BOARD_LAYOUT' 'is:open Статус:"В работе"'),
    (New-View '03 — Проверка' 'C3' 'BOARD_LAYOUT' 'is:open Статус:"Проверка QA"'),
    (New-View '04 — Заблокировано' 'C4' 'TABLE_LAYOUT' 'is:open Статус:"Заблокировано"')
  )
}

$tokens=$null
$parseErrors=$null
$productionAst=[System.Management.Automation.Language.Parser]::ParseFile($scriptPath,[ref]$tokens,[ref]$parseErrors)
if(@($parseErrors).Count -gt 0){
  throw "Production configure_project.ps1 не разбирается PowerShell Parser: $((@($parseErrors)|ForEach-Object{$_.Message}) -join '; ')"
}

$entrypointCommands=@($productionAst.FindAll({
  param($node)
  if($node -isnot [System.Management.Automation.Language.CommandAst]){return $false}
  return $node.GetCommandName() -ceq 'Invoke-ProjectConfiguration'
},$true))
if($entrypointCommands.Count -ne 1){
  throw "В production-скрипте должна быть ровно одна фактическая команда Invoke-ProjectConfiguration; найдено $($entrypointCommands.Count)."
}

$applyExpressions=@($entrypointCommands[0].CommandElements|Where-Object{$_ -is [System.Management.Automation.Language.ScriptBlockExpressionAst]})
if($applyExpressions.Count -ne 1){
  throw 'Production Invoke-ProjectConfiguration должен получать ровно одно фактическое тело Apply.'
}
$script:ProductionApplyAst=$applyExpressions[0].ScriptBlock
$script:ProductionApply=$script:ProductionApplyAst.GetScriptBlock()

$mutationEntryCommands=@('EnsureLink','EnsureSelect','EnsureIteration','EnsureItems','EnsureViews')
$allMutationEntryCalls=@($productionAst.FindAll({
  param($node)
  if($node -isnot [System.Management.Automation.Language.CommandAst]){return $false}
  $name=$node.GetCommandName()
  return $mutationEntryCommands -ccontains $name
},$true))

foreach($call in $allMutationEntryCalls){
  $insideApply=($call.Extent.StartOffset -ge $script:ProductionApplyAst.Extent.StartOffset -and $call.Extent.EndOffset -le $script:ProductionApplyAst.Extent.EndOffset)
  $insideFunction=$false
  $parent=$call.Parent
  while($null -ne $parent){
    if($parent -is [System.Management.Automation.Language.FunctionDefinitionAst]){
      $insideFunction=$true
      break
    }
    $parent=$parent.Parent
  }
  if(-not $insideFunction -and -not $insideApply){
    throw "Production mutation-команда '$($call.GetCommandName())' находится вне защищённого тела Invoke-ProjectConfiguration."
  }
}

$productionApplyCalls=@($script:ProductionApplyAst.FindAll({
  param($node)
  if($node -isnot [System.Management.Automation.Language.CommandAst]){return $false}
  return $mutationEntryCommands -ccontains $node.GetCommandName()
},$true)|ForEach-Object{$_.GetCommandName()})
if($productionApplyCalls.Count -ne 16){
  throw "Фактическое production-тело entrypoint изменилось: ожидаются 16 управляющих вызовов, найдено $($productionApplyCalls.Count)."
}
if($productionApplyCalls[0] -cne 'EnsureLink' -or $productionApplyCalls[-3] -cne 'EnsureIteration' -or $productionApplyCalls[-2] -cne 'EnsureItems' -or $productionApplyCalls[-1] -cne 'EnsureViews'){
  throw "Нарушен порядок фактического production entrypoint: EnsureLink должен быть первым, затем поля, затем EnsureIteration -> EnsureItems -> EnsureViews."
}
if(@($productionApplyCalls|Where-Object{$_ -ceq 'EnsureSelect'}).Count -ne 12){
  throw 'Фактическое production-тело entrypoint должно содержать 12 вызовов EnsureSelect.'
}

function Snapshot {
  if($null -ne $script:CustomFields){
    return [pscustomobject]@{
      user=[pscustomobject]@{
        projectV2=[pscustomobject]@{
          id='PROJECT'
          title='KAT9I_OS — разработка'
          repositories=[pscustomobject]@{nodes=@([pscustomobject]@{id='REPO';nameWithOwner='rassvetpublic-spec/KAT9I_OS'})}
          fields=[pscustomobject]@{nodes=@($script:CustomFields)}
          views=[pscustomobject]@{nodes=@()}
        }
      }
      repository=[pscustomobject]@{id='REPO';nameWithOwner='rassvetpublic-spec/KAT9I_OS'}
    }
  }
  if($script:IterationMode){
    $iteration=[pscustomobject]@{
      id='ITER'
      name='Итерация'
      __typename='ProjectV2IterationField'
      configuration=[pscustomobject]@{duration=$script:IterationDuration;startDay=1}
    }
    return [pscustomobject]@{
      user=[pscustomobject]@{
        projectV2=[pscustomobject]@{
          id='PROJECT'
          fields=[pscustomobject]@{nodes=@($iteration)}
          views=[pscustomobject]@{nodes=@()}
        }
      }
    }
  }

  $fields=@()
  $i=1
  foreach($name in $script:Required){
    $fields+=[pscustomobject]@{id="F$i";name=$name;__typename='ProjectV2Field'}
    $i++
  }
  [pscustomobject]@{
    user=[pscustomobject]@{
      projectV2=[pscustomobject]@{
        id='PROJECT'
        title='KAT9I_OS — разработка'
        repositories=[pscustomobject]@{nodes=@([pscustomobject]@{id='REPO';nameWithOwner='rassvetpublic-spec/KAT9I_OS'})}
        fields=[pscustomobject]@{nodes=$fields}
        views=[pscustomobject]@{nodes=$script:MockViews}
      }
    }
    repository=[pscustomobject]@{id='REPO';nameWithOwner='rassvetpublic-spec/KAT9I_OS'}
  }
}

function Rest {
  param([string]$Endpoint,[string]$Method='GET',$Body=$null)
  if($Method -ne 'GET'){
    $script:RestWrites++
    throw "Неожиданная запись REST: $Endpoint"
  }
  if($Endpoint -like 'users/*/projectsV2/*/fields*'){
    $out=@()
    $i=1
    foreach($name in $script:Required){
      $out+=[pscustomobject]@{id=[int64]$i;name=$name}
      $i++
    }
    return $out
  }
  if($Endpoint -eq "users/$Owner"){
    return [pscustomobject]@{id='123'}
  }
  throw "Неожиданный GET REST: $Endpoint"
}

function Gql {
  param([string]$Query,[hashtable]$Variables)
  $script:GqlCalls++
  throw 'GraphQL mutation не должна выполняться в fail-closed сценарии.'
}

function gh {
  $global:LASTEXITCODE=0
  if($args.Count -ge 2 -and $args[0] -eq 'issue' -and $args[1] -eq 'list'){return '[]'}
  if($args.Count -ge 2 -and $args[0] -eq 'pr' -and $args[1] -eq 'list'){return '[]'}
  if($args.Count -ge 2 -and $args[0] -eq 'project' -and $args[1] -eq 'item-add'){
    $script:ItemAddCalls++
    return '{}'
  }
  throw "Неожиданный вызов gh в тесте production entrypoint: $($args -join ' ')"
}

function Assert-ViewsFailClosed([object[]]$Views,[string]$ExpectedMessage){
  $script:IterationMode=$false
  $script:MockViews=$Views
  $script:GqlCalls=0
  $script:RestWrites=0
  $thrown=$false
  try {
    EnsureViews
  } catch {
    $thrown=$true
    if($_.Exception.Message -notmatch $ExpectedMessage){
      throw "Получена другая ошибка: $($_.Exception.Message)"
    }
  }
  if(-not $thrown){throw 'Ожидалась fail-closed ошибка, но EnsureViews завершился успешно.'}
  if($script:GqlCalls -ne 0){throw "Fail-closed нарушен: GraphQL mutation calls = $($script:GqlCalls)"}
  if($script:RestWrites -ne 0){throw "Fail-closed нарушен: REST writes = $($script:RestWrites)"}
}

function Assert-EntrypointFailClosed([object[]]$Views,[string]$ExpectedMessage){
  $script:IterationMode=$false
  $script:MockViews=$Views
  $script:GqlCalls=0
  $script:RestWrites=0
  $script:ItemAddCalls=0
  $thrown=$false
  try {
    Invoke-ProjectConfiguration $script:ProductionApply
  } catch {
    $thrown=$true
    if($_.Exception.Message -notmatch $ExpectedMessage){
      throw "Получена другая ошибка production entrypoint: $($_.Exception.Message)"
    }
  }
  if(-not $thrown){throw 'Ожидалась fail-closed ошибка production entrypoint, но фактическое тело Apply было разрешено.'}
  if($script:GqlCalls -ne 0){throw "Production entrypoint fail-closed нарушен: GraphQL mutations = $($script:GqlCalls)"}
  if($script:RestWrites -ne 0){throw "Production entrypoint fail-closed нарушен: REST writes = $($script:RestWrites)"}
  if($script:ItemAddCalls -ne 0){throw "Production entrypoint fail-closed нарушен: item-add calls = $($script:ItemAddCalls)"}
}

$caseVariant=@(New-CanonicalViews | Where-Object{$_.name -cne '00 — Все задачи'})
$caseVariant+=New-View '00 — все задачи' 'CASE' 'TABLE_LAYOUT' 'is:open'
Assert-ViewsFailClosed $caseVariant 'неизвестные или регистрово отличающиеся представления'
Assert-EntrypointFailClosed $caseVariant 'неизвестные или регистрово отличающиеся представления'

$oldQaFilter=@(New-CanonicalViews)
$oldQaFilter=@($oldQaFilter|ForEach-Object{
  if($_.name -ceq '03 — Проверка'){
    New-View $_.name $_.id $_.layout 'is:open Статус:"Проверка качества"'
  } else {$_}
})
Assert-ViewsFailClosed $oldQaFilter 'нарушает контракт'
Assert-EntrypointFailClosed $oldQaFilter 'нарушает контракт'

$missingEarlyDuplicateLate=@(New-CanonicalViews | Where-Object{$_.name -cne '00 — Все задачи'})
$missingEarlyDuplicateLate+=New-View '03 — Проверка' 'DUP' 'BOARD_LAYOUT' 'is:open Статус:"Проверка QA"'
Assert-ViewsFailClosed $missingEarlyDuplicateLate 'дубли представления'
Assert-EntrypointFailClosed $missingEarlyDuplicateLate 'дубли представления'

$script:IterationMode=$true
$script:IterationDuration=7
$script:GqlCalls=0
$thrown=$false
try {
  EnsureIteration
} catch {
  $thrown=$true
  if($_.Exception.Message -notmatch 'не сбрасывает существующие периоды'){
    throw "Получена другая ошибка итерации: $($_.Exception.Message)"
  }
}
if(-not $thrown){throw 'Ожидалась fail-closed ошибка для существующей 7-дневной итерации.'}
if($script:GqlCalls -ne 0){throw "Итерация была изменена через GraphQL: calls = $($script:GqlCalls)"}

$script:IterationMode=$false
$script:CustomFields=@(
  [pscustomobject]@{id='F1';name='Статус';__typename='ProjectV2SingleSelectField';options=@()},
  [pscustomobject]@{id='F2';name='Status';__typename='ProjectV2SingleSelectField';options=@()}
)
$script:GqlCalls=0
$thrown=$false
try {
  EnsureSelect 'Статус' @('Статус','Status') @((Opt 'Входящие' 'GRAY' 'Новая задача' @('Входящие','Todo')))
} catch {
  $thrown=$true
  if($_.Exception.Message -notmatch 'неоднозначные поля Project'){
    throw "Получена другая ошибка дублирующихся полей: $($_.Exception.Message)"
  }
}
if(-not $thrown){throw 'Ожидалась fail-closed ошибка для канонического поля и его alias.'}
if($script:GqlCalls -ne 0){throw "Дублирующиеся поля вызвали GraphQL mutation: calls = $($script:GqlCalls)"}

$script:CustomFields=@(
  [pscustomobject]@{
    id='F1'
    name='Статус'
    __typename='ProjectV2SingleSelectField'
    options=@(
      [pscustomobject]@{id='O1';name='Входящие'},
      [pscustomobject]@{id='O2';name='Todo'}
    )
  }
)
$script:GqlCalls=0
$thrown=$false
try {
  EnsureSelect 'Статус' @('Статус','Status') @((Opt 'Входящие' 'GRAY' 'Новая задача' @('Входящие','Todo')))
} catch {
  $thrown=$true
  if($_.Exception.Message -notmatch 'неоднозначные значения'){
    throw "Получена другая ошибка дублирующихся значений: $($_.Exception.Message)"
  }
}
if(-not $thrown){throw 'Ожидалась fail-closed ошибка для канонического значения и его alias.'}
if($script:GqlCalls -ne 0){throw "Дублирующиеся значения вызвали GraphQL mutation: calls = $($script:GqlCalls)"}
$script:CustomFields=$null

Write-Host 'PASS: Project policy запускает фактическое production-тело entrypoint под read-only preflight; mutation-вызовы вне защищённого Apply запрещены, а case-variant, старый QA filter и дубль дают 0 REST writes / 0 GraphQL mutations / 0 item-add.'
