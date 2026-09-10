Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$scriptPath=Join-Path $PSScriptRoot '..' 'scripts' 'project_queue_sync.ps1'
. $scriptPath -LibraryMode -Url 'https://github.com/rassvetpublic-spec/KAT9I_OS/issues/117' -State ACTIVE

function Assert-Equal($Expected,$Actual,[string]$Message){
  if($Expected -cne $Actual){throw "$Message Ожидалось='$Expected', фактически='$Actual'."}
}
function Assert-HasKey($Map,[string]$Key,[string]$Message){
  if(-not $Map.Contains($Key)){throw $Message}
}
function Assert-NoKey($Map,[string]$Key,[string]$Message){
  if($Map.Contains($Key)){throw $Message}
}
function Assert-ContainsArg($Parts,[string]$Arg,[string]$Message){
  if(-not ($Parts -contains $Arg)){throw $Message}
}
function Assert-NoArg($Parts,[string]$Arg,[string]$Message){
  if($Parts -contains $Arg){throw $Message}
}

$expected=@{
  INBOX=@('Входящие','Свободно','Нет')
  READY=@('Готово к работе','Свободно','Нет')
  ACTIVE=@('В работе','Активно','Частично')
  QA=@('Проверка QA','На проверке','Частично')
  QUEUED=@('Проверка QA','В очереди','Проверка качества пройдена')
}
foreach($stateName in $expected.Keys){
  $p=QueueProfile $stateName 'ChatGPT' 'Антигравити'
  Assert-Equal $expected[$stateName][0] $p['Статус'] "Неверный Статус для $stateName."
  Assert-Equal $expected[$stateName][1] $p['Исполнение'] "Неверное Исполнение для $stateName."
  Assert-Equal $expected[$stateName][2] $p['Доказательство'] "Неверное Доказательство для $stateName."
}
$blocked=QueueProfile 'BLOCKED' 'ChatGPT' 'Antigravity'
Assert-Equal 'Заблокировано' $blocked['Статус'] 'Неверный Статус для BLOCKED.'
Assert-Equal 'Заблокировано' $blocked['Исполнение'] 'Неверное Исполнение для BLOCKED.'
Assert-NoKey $blocked 'Доказательство' 'BLOCKED не должен выдумывать уровень Evidence.'
$done=QueueProfile 'DONE' 'ChatGPT' 'Agy'
Assert-Equal 'Готово' $done['Статус'] 'Неверный Статус для DONE.'
Assert-Equal 'Освобождено' $done['Исполнение'] 'Неверное Исполнение для DONE.'
Assert-NoKey $done 'Доказательство' 'DONE не должен выдумывать QA Evidence.'

foreach($alias in @('AGY','Agy','Antigravity','Антигравити','Antigravity (AGY)','Антигравити (AGY)')){
  Assert-Equal 'AGY' (Normalize-QaWorker $alias) "QA alias '$alias' должен нормализоваться в одну Project identity."
}
Assert-Equal '' (Normalize-QaWorker '') 'Пустой QA Worker должен означать preserve existing assignment.'

foreach($stateName in @('ACTIVE','QA','QUEUED')){
  $p=QueueProfile $stateName 'Codex' 'Antigravity (AGY)'
  Assert-HasKey $p 'Исполнитель' "$stateName должен фиксировать явно переданного Исполнителя."
  Assert-HasKey $p 'Проверяющий' "$stateName должен фиксировать явно переданного Проверяющего."
  Assert-Equal 'Codex' $p['Исполнитель'] "Неверный Исполнитель для $stateName."
  Assert-Equal 'AGY' $p['Проверяющий'] "Проверяющий должен храниться как стабильная Project identity AGY."
}
$customQa=QueueProfile 'QA' 'ChatGPT' 'Codex'
Assert-Equal 'Codex' $customQa['Проверяющий'] 'Поддерживаемый custom QA Worker должен передаваться без подмены.'
foreach($stateName in @('ACTIVE','QA','QUEUED')){
  $p=QueueProfile $stateName '' ''
  Assert-NoKey $p 'Исполнитель' "$stateName без metadata должен сохранить существующего Исполнителя."
  Assert-NoKey $p 'Проверяющий' "$stateName без metadata должен сохранить существующего Проверяющего."
}

$script:Calls=@()
$script:FailAccess=$false
$script:FailFieldId=$null
$script:MissingItem=$false
$script:MissingOption=$null

function New-Option([string]$Id,[string]$Name){
  return [pscustomobject]@{id=$Id;name=$Name}
}
function New-Field([string]$Id,[string]$Name,[object[]]$Options){
  return [pscustomobject]@{__typename='ProjectV2SingleSelectField';id=$Id;name=$Name;options=$Options}
}
function ProjectFieldsJson{
  $fields=@(
    (New-Field 'F_WORKER' 'Исполнитель' @(
      (New-Option 'O_WORKER_CHATGPT' 'ChatGPT'),
      (New-Option 'O_WORKER_CODEX' 'Codex')
    )),
    (New-Field 'F_QA' 'Проверяющий' @(
      (New-Option 'O_QA_AGY' 'AGY'),
      (New-Option 'O_QA_CODEX' 'Codex')
    )),
    (New-Field 'F_EVIDENCE' 'Доказательство' @(
      (New-Option 'O_E_NONE' 'Нет'),
      (New-Option 'O_E_PART' 'Частично'),
      (New-Option 'O_E_AUTO' 'Автопроверки пройдены'),
      (New-Option 'O_E_QA' 'Проверка качества пройдена')
    )),
    (New-Field 'F_EXECUTION' 'Исполнение' @(
      (New-Option 'O_X_FREE' 'Свободно'),
      (New-Option 'O_X_ACTIVE' 'Активно'),
      (New-Option 'O_X_REVIEW' 'На проверке'),
      (New-Option 'O_X_QUEUE' 'В очереди'),
      (New-Option 'O_X_BLOCK' 'Заблокировано'),
      (New-Option 'O_X_RELEASED' 'Освобождено')
    )),
    (New-Field 'F_STATUS' 'Status' @(
      (New-Option 'O_S_INBOX' 'Входящие'),
      (New-Option 'O_S_READY' 'Готово к работе'),
      (New-Option 'O_S_ACTIVE' 'В работе'),
      (New-Option 'O_S_QA' 'Проверка QA'),
      (New-Option 'O_S_BLOCK' 'Заблокировано'),
      (New-Option 'O_S_DONE' 'Готово')
    ))
  )

  if($null -ne $script:MissingOption){
    foreach($field in $fields){
      $field.options=@($field.options|Where-Object{$_.name -cne $script:MissingOption})
    }
  }

  return ([pscustomobject]@{
    data=[pscustomobject]@{
      node=[pscustomobject]@{
        fields=[pscustomobject]@{nodes=$fields}
      }
    }
  } | ConvertTo-Json -Depth 20 -Compress)
}

function gh {
  $parts=@($args|ForEach-Object{[string]$_})
  $script:Calls+=,($parts)

  if($parts.Count -ge 2 -and $parts[0] -eq 'project' -and $parts[1] -eq 'view'){
    if($script:FailAccess){$global:LASTEXITCODE=1;return 'denied'}
    $global:LASTEXITCODE=0
    return '{"id":"PVT_PROJECT"}'
  }

  if($parts.Count -ge 2 -and $parts[0] -eq 'project' -and $parts[1] -eq 'item-list'){
    $global:LASTEXITCODE=0
    if($script:MissingItem){return '{"items":[]}' }
    return ([pscustomobject]@{
      items=@(
        [pscustomobject]@{
          id='PVTI_ITEM'
          content=[pscustomobject]@{url=$Url}
        }
      )
    } | ConvertTo-Json -Depth 10 -Compress)
  }

  if($parts.Count -ge 2 -and $parts[0] -eq 'api' -and $parts[1] -eq 'graphql'){
    $global:LASTEXITCODE=0
    return (ProjectFieldsJson)
  }

  if($parts.Count -ge 2 -and $parts[0] -eq 'project' -and $parts[1] -eq 'item-edit'){
    $fieldIndex=[Array]::IndexOf($parts,'--field-id')
    $fieldId=$parts[$fieldIndex+1]
    if($null -ne $script:FailFieldId -and $fieldId -ceq $script:FailFieldId){
      $global:LASTEXITCODE=1
      return 'fail'
    }
    $global:LASTEXITCODE=0
    return '{}'
  }

  throw "Неожиданный gh: $($parts -join ' ')"
}

$State='QUEUED'
$Worker='Codex'
$QaWorker='Antigravity (AGY)'
$script:Calls=@()
Sync-ProjectQueueState

$edits=@($script:Calls|Where-Object{$_.Count -ge 2 -and $_[0] -eq 'project' -and $_[1] -eq 'item-edit'})
if($edits.Count -ne 5){throw "Ожидалось 5 item-edit, получено $($edits.Count)."}

$fieldIds=@($edits|ForEach-Object{$_[[Array]::IndexOf($_,'--field-id')+1]})
Assert-Equal 'F_WORKER,F_QA,F_EVIDENCE,F_EXECUTION,F_STATUS' ($fieldIds -join ',') 'Нарушен порядок commit-marker.'

foreach($call in $edits){
  Assert-ContainsArg $call '--id' 'item-edit должен использовать item id.'
  Assert-ContainsArg $call '--project-id' 'item-edit должен использовать project id.'
  Assert-ContainsArg $call '--field-id' 'item-edit должен использовать field id.'
  Assert-ContainsArg $call '--single-select-option-id' 'item-edit должен использовать option id.'
  Assert-NoArg $call '--owner' 'Машинный item-edit не должен зависеть от owner-name режима.'
  Assert-NoArg $call '--url' 'Машинный item-edit не должен зависеть от url-name режима.'
  Assert-NoArg $call '--field' 'Машинный item-edit не должен зависеть от field-name режима.'
  Assert-NoArg $call '--value' 'Машинный item-edit не должен зависеть от value-name режима.'
}
$qaCall=@($edits|Where-Object{$_[[Array]::IndexOf($_,'--field-id')+1] -ceq 'F_QA'})[0]
Assert-Equal 'O_QA_AGY' $qaCall[[Array]::IndexOf($qaCall,'--single-select-option-id')+1] 'Compound Antigravity alias должен записываться через стабильный option ID AGY.'

$State='QA'
$Worker='ChatGPT'
$QaWorker='Codex'
$script:Calls=@()
Sync-ProjectQueueState
$customQaEdits=@($script:Calls|Where-Object{$_.Count -ge 2 -and $_[0] -eq 'project' -and $_[1] -eq 'item-edit'})
$customQaCall=@($customQaEdits|Where-Object{$_[[Array]::IndexOf($_,'--field-id')+1] -ceq 'F_QA'})[0]
Assert-Equal 'O_QA_CODEX' $customQaCall[[Array]::IndexOf($customQaCall,'--single-select-option-id')+1] 'Custom QA Codex должен использовать собственный Project option ID.'

$State='QUEUED'
$Worker='Codex'
$QaWorker='AGY'
$script:Calls=@()
$script:FailAccess=$true
$failed=$false
try{Sync-ProjectQueueState}catch{$failed=$true;if($_.Exception.Message -notmatch 'Чтение Project'){throw}}
if(-not $failed){throw 'Ожидалась fail-closed ошибка Project access.'}
if(@($script:Calls|Where-Object{$_.Count -ge 2 -and $_[1] -eq 'item-edit'}).Count -ne 0){throw 'После ошибки access были записи Project.'}
$script:FailAccess=$false

$script:Calls=@()
$script:MissingItem=$true
$failed=$false
try{Sync-ProjectQueueState}catch{$failed=$true;if($_.Exception.Message -notmatch 'Карточка'){throw}}
if(-not $failed){throw 'Ожидалась fail-closed ошибка отсутствующего Project item.'}
if(@($script:Calls|Where-Object{$_.Count -ge 2 -and $_[1] -eq 'item-edit'}).Count -ne 0){throw 'При отсутствующей карточке были записи Project.'}
$script:MissingItem=$false

$script:Calls=@()
$script:MissingOption='Проверка качества пройдена'
$failed=$false
try{Sync-ProjectQueueState}catch{$failed=$true;if($_.Exception.Message -notmatch 'Проверка качества пройдена'){throw}}
if(-not $failed){throw 'Ожидалась fail-closed ошибка отсутствующего option ID.'}
if(@($script:Calls|Where-Object{$_.Count -ge 2 -and $_[1] -eq 'item-edit'}).Count -ne 0){throw 'Preflight ID resolution должен завершиться до первой записи.'}
$script:MissingOption=$null

$script:Calls=@()
$script:FailFieldId='F_EVIDENCE'
$failed=$false
try{Sync-ProjectQueueState}catch{$failed=$true;if($_.Exception.Message -notmatch 'Доказательство'){throw}}
if(-not $failed){throw 'Ожидалась ошибка записи поля.'}
$writtenFieldIds=@($script:Calls|Where-Object{$_.Count -ge 2 -and $_[1] -eq 'item-edit'}|ForEach-Object{$_[[Array]::IndexOf($_,'--field-id')+1]})
if($writtenFieldIds -contains 'F_STATUS'){throw 'Статус не должен меняться после промежуточного сбоя.'}
if($writtenFieldIds -contains 'F_EXECUTION'){throw 'Исполнение не должно меняться после сбоя Evidence.'}
$script:FailFieldId=$null

$oldUrl=$Url
$Url='https://github.com/other/repo/issues/1'
$script:Calls=@()
$failed=$false
try{Sync-ProjectQueueState}catch{$failed=$true;if($_.Exception.Message -notmatch 'не является Issue/PR репозитория'){throw}}
if(-not $failed){throw 'Чужой URL должен блокироваться fail-closed.'}
if($script:Calls.Count -ne 0){throw 'Чужой URL должен блокироваться до любого обращения к Project.'}
$Url=$oldUrl

Write-Host 'PASS: Project queue identity metadata, ID-based edits и commit-marker работают fail-closed.'
