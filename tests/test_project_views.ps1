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

function New-View([string]$Name,[string]$Id){
  [pscustomobject]@{id=$Id;name=$Name;layout='TABLE';filter=''}
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

$canonical=@(
  '00 — Все задачи',
  '01 — Готово к работе',
  '02 — В работе',
  '03 — Проверка',
  '04 — Заблокировано'
)

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

$caseVariant=@()
$i=1
foreach($name in $canonical){$caseVariant+=New-View $name "C$i";$i++}
$caseVariant+=New-View '00 — все задачи' 'CASE'
Assert-ViewsFailClosed $caseVariant 'неизвестные дополнительные представления'

$duplicate=@()
$i=1
foreach($name in $canonical){$duplicate+=New-View $name "D$i";$i++}
$duplicate+=New-View '00 — Все задачи' 'DUP'
Assert-ViewsFailClosed $duplicate 'дубли канонического представления'

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

Write-Host 'PASS: Project policy fail-closed для case-variant, дубля и небезопасной миграции итерации.'
