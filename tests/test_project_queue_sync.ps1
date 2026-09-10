Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$scriptPath=Join-Path $PSScriptRoot '..' 'scripts' 'project_queue_sync.ps1'
. $scriptPath -LibraryMode -Url 'https://github.com/rassvetpublic-spec/KAT9I_OS/issues/112' -State ACTIVE

function Assert-Equal($Expected,$Actual,[string]$Message){
  if($Expected -cne $Actual){throw "$Message Ожидалось='$Expected', фактически='$Actual'."}
}
function Assert-HasKey($Map,[string]$Key,[string]$Message){
  if(-not $Map.Contains($Key)){throw $Message}
}
function Assert-NoKey($Map,[string]$Key,[string]$Message){
  if($Map.Contains($Key)){throw $Message}
}

$expected=@{
  READY=@('Готово к работе','Свободно','Нет')
  ACTIVE=@('В работе','Активно','Частично')
  QA=@('Проверка QA','На проверке','Частично')
  QUEUED=@('Проверка QA','В очереди','Проверка качества пройдена')
  BLOCKED=@('Заблокировано','Заблокировано','Частично')
}
foreach($stateName in $expected.Keys){
  $p=QueueProfile $stateName 'ChatGPT' 'Антигравити'
  Assert-Equal $expected[$stateName][0] $p['Статус'] "Неверный Статус для $stateName."
  Assert-Equal $expected[$stateName][1] $p['Исполнение'] "Неверное Исполнение для $stateName."
  Assert-Equal $expected[$stateName][2] $p['Доказательство'] "Неверное Доказательство для $stateName."
}
$done=QueueProfile 'DONE' 'ChatGPT' 'Антигравити'
Assert-Equal 'Готово' $done['Статус'] 'Неверный Статус для DONE.'
Assert-Equal 'Освобождено' $done['Исполнение'] 'Неверное Исполнение для DONE.'
Assert-NoKey $done 'Доказательство' 'DONE не должен выдумывать QA Evidence.'

foreach($stateName in @('ACTIVE','QA','QUEUED')){
  $p=QueueProfile $stateName 'ChatGPT' 'Антигравити'
  Assert-HasKey $p 'Исполнитель' "$stateName должен фиксировать Исполнителя."
  Assert-HasKey $p 'Проверяющий' "$stateName должен фиксировать Проверяющего."
  Assert-Equal 'ChatGPT' $p['Исполнитель'] "Неверный Исполнитель для $stateName."
  Assert-Equal 'Антигравити' $p['Проверяющий'] "Неверный Проверяющий для $stateName."
}
foreach($stateName in @('READY','BLOCKED','DONE')){
  $p=QueueProfile $stateName 'ChatGPT' 'Антигравити'
  Assert-NoKey $p 'Исполнитель' "$stateName не должен автоматически приписывать ChatGPT."
  Assert-NoKey $p 'Проверяющий' "$stateName не должен автоматически приписывать Антигравити."
}

$script:Calls=@()
$script:FailAccess=$false
$script:FailField=$null
function gh {
  $parts=@($args|ForEach-Object{[string]$_})
  $script:Calls+=,($parts)
  if($parts.Count -ge 2 -and $parts[0] -eq 'project' -and $parts[1] -eq 'view'){
    if($script:FailAccess){$global:LASTEXITCODE=1;return 'denied'}
    $global:LASTEXITCODE=0;return '{}'
  }
  if($parts.Count -ge 2 -and $parts[0] -eq 'project' -and $parts[1] -eq 'item-edit'){
    $fieldIndex=[Array]::IndexOf($parts,'--field')
    $field=$parts[$fieldIndex+1]
    if($null -ne $script:FailField -and $field -ceq $script:FailField){$global:LASTEXITCODE=1;return 'fail'}
    $global:LASTEXITCODE=0;return '{}'
  }
  throw "Неожиданный gh: $($parts -join ' ')"
}

$State='QUEUED'
$Worker='ChatGPT'
$QaWorker='Антигравити'
$script:Calls=@()
Sync-ProjectQueueState
$edits=@($script:Calls|Where-Object{$_[1] -eq 'item-edit'})
if($edits.Count -ne 5){throw "Ожидалось 5 item-edit, получено $($edits.Count)."}
$fields=@($edits|ForEach-Object{$_[[Array]::IndexOf($_,'--field')+1]})
Assert-Equal 'Исполнитель,Проверяющий,Доказательство,Исполнение,Статус' ($fields -join ',') 'Нарушен порядок commit-marker.'
$qaCall=@($edits|Where-Object{$_[[Array]::IndexOf($_,'--field')+1] -ceq 'Проверяющий'})[0]
Assert-Equal 'Антигравити' $qaCall[[Array]::IndexOf($qaCall,'--value')+1] 'QA Worker должен быть Антигравити.'

$script:Calls=@();$script:FailAccess=$true
$failed=$false
try{Sync-ProjectQueueState}catch{$failed=$true;if($_.Exception.Message -notmatch 'scope project'){throw}}
if(-not $failed){throw 'Ожидалась fail-closed ошибка Project access.'}
if(@($script:Calls|Where-Object{$_[1] -eq 'item-edit'}).Count -ne 0){throw 'После ошибки access были записи Project.'}
$script:FailAccess=$false

$script:Calls=@();$script:FailField='Доказательство'
$failed=$false
try{Sync-ProjectQueueState}catch{$failed=$true;if($_.Exception.Message -notmatch 'Доказательство'){throw}}
if(-not $failed){throw 'Ожидалась ошибка записи поля.'}
$writtenFields=@($script:Calls|Where-Object{$_[1] -eq 'item-edit'}|ForEach-Object{$_[[Array]::IndexOf($_,'--field')+1]})
if($writtenFields -contains 'Статус'){throw 'Статус не должен меняться после промежуточного сбоя.'}
if($writtenFields -contains 'Исполнение'){throw 'Исполнение не должно меняться после сбоя Evidence.'}
$script:FailField=$null

Write-Host 'PASS: Project queue lifecycle и commit-marker работают fail-closed.'
