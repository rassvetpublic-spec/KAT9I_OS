Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$scriptPath=Join-Path $PSScriptRoot '..' 'scripts' 'configure_project.ps1'
. $scriptPath -LibraryMode

function Start-Sleep { param([int]$Seconds) }

$script:Required=@('Статус','Этап','Приоритет','Область','Исполнитель','Проверяющий','Исполнение')
$script:MockViews=@()
$script:GqlCalls=0
$script:RestWrites=0

function New-View([string]$Name,[string]$Id){
  [pscustomobject]@{id=$Id;name=$Name;layout='TABLE';filter=''}
}

function Snapshot {
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
  throw 'Удаление/GraphQL mutation не должно выполняться в fail-closed сценарии.'
}

$canonical=@(
  '00 — Все задачи',
  '01 — Готово к работе',
  '02 — В работе',
  '03 — Проверка',
  '04 — Заблокировано'
)

function Assert-FailClosed([object[]]$Views,[string]$ExpectedMessage){
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
Assert-FailClosed $caseVariant 'неизвестные дополнительные представления'

$duplicate=@()
$i=1
foreach($name in $canonical){$duplicate+=New-View $name "D$i";$i++}
$duplicate+=New-View '00 — Все задачи' 'DUP'
Assert-FailClosed $duplicate 'дубли канонического представления'

Write-Host 'PASS: EnsureViews fail-closed для case-variant и дубля без mutation/delete.'
