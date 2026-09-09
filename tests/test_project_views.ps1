Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$scriptPath=Join-Path $PSScriptRoot '..' 'scripts' 'configure_project.ps1'
. $scriptPath -LibraryMode

function Start-Sleep { param([int]$Seconds) }

$script:Required=@('Статус','Этап','Приоритет','Область','Исполнитель','Проверяющий','Исполнение')
$script:MockViews=@()
$script:GqlCalls=0
$script:RestWrites=0
$script:IterationMode=$false
$script:IterationDuration=3

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

function Snapshot {
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
        fields=[pscustomobject]@{nodes=$fields}
        views=[pscustomobject]@{nodes=$script:MockViews}
      }
    }
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

$caseVariant=@(New-CanonicalViews | Where-Object{$_.name -cne '00 — Все задачи'})
$caseVariant+=New-View '00 — все задачи' 'CASE' 'TABLE_LAYOUT' 'is:open'
Assert-ViewsFailClosed $caseVariant 'неизвестные или регистрово отличающиеся представления'

$oldQaFilter=@(New-CanonicalViews)
$oldQaFilter=@($oldQaFilter|ForEach-Object{
  if($_.name -ceq '03 — Проверка'){
    New-View $_.name $_.id $_.layout 'is:open Статус:"Проверка качества"'
  } else {$_}
})
Assert-ViewsFailClosed $oldQaFilter 'нарушает контракт'

$missingEarlyDuplicateLate=@(New-CanonicalViews | Where-Object{$_.name -cne '00 — Все задачи'})
$missingEarlyDuplicateLate+=New-View '03 — Проверка' 'DUP' 'BOARD_LAYOUT' 'is:open Статус:"Проверка QA"'
Assert-ViewsFailClosed $missingEarlyDuplicateLate 'дубли представления'

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

Write-Host 'PASS: Project policy fail-closed выполняет полный preflight имени/layout/filter, дублей и небезопасной миграции итерации.'