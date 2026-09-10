Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$scriptPath=Join-Path $PSScriptRoot '..' 'scripts' 'project_queue_sync.ps1'
. $scriptPath -LibraryMode -Url 'https://github.com/rassvetpublic-spec/KAT9I_OS/issues/116' -State ACTIVE

function Assert-Equal($Expected,$Actual,[string]$Message){
  if($Expected -cne $Actual){throw "$Message Ожидалось='$Expected', фактически='$Actual'."}
}
function Assert-True([bool]$Value,[string]$Message){if(-not $Value){throw $Message}}
function Assert-NoEdits([string]$Message){
  $edits=@($script:Calls|Where-Object{$_.Count -ge 2 -and $_[0] -eq 'project' -and $_[1] -eq 'item-edit'})
  if($edits.Count -ne 0){throw $Message}
}
function Assert-Code([string]$Expected,[scriptblock]$Action){
  $failed=$false
  try{& $Action}catch{
    $failed=$true
    if($_.Exception.Message -notmatch "KAT9I_PROJECT_PREFLIGHT=$Expected"){throw}
    if(-not [string]::IsNullOrWhiteSpace($script:SecretProbe) -and $_.Exception.Message.Contains($script:SecretProbe)){
      throw 'Диагностика не должна печатать secret material.'
    }
  }
  if(-not $failed){throw "Ожидался diagnostic code $Expected."}
}

foreach($alias in @('AGY','Agy','Antigravity','Антигравити','Antigravity (AGY)','Антигравити (AGY)')){
  Assert-Equal 'AGY' (Normalize-QaWorker $alias) "QA alias '$alias' должен нормализоваться в AGY."
}

$script:Calls=@()
$script:FailToken=$false
$script:FailAccess=$false
$script:CanUpdate=$true
$script:GraphQlFail=$false
$script:MissingItem=$false
$script:MissingOption=$null
$script:FailFieldId=$null
$script:FailFieldText='fail'
$script:SecretProbe='TEST_SECRET_VALUE_DO_NOT_PRINT'
$env:GH_TOKEN=$script:SecretProbe

function New-Option([string]$Id,[string]$Name){[pscustomobject]@{id=$Id;name=$Name}}
function New-Field([string]$Id,[string]$Name,[object[]]$Options){
  [pscustomobject]@{__typename='ProjectV2SingleSelectField';id=$Id;name=$Name;options=$Options}
}
function ProjectSnapshotJson{
  $fields=@(
    (New-Field 'F_WORKER' 'Исполнитель' @((New-Option 'O_WORKER_CHATGPT' 'ChatGPT'),(New-Option 'O_WORKER_CODEX' 'Codex'))),
    (New-Field 'F_QA' 'Проверяющий' @((New-Option 'O_QA_AGY' 'AGY'),(New-Option 'O_QA_CODEX' 'Codex'))),
    (New-Field 'F_EVIDENCE' 'Доказательство' @((New-Option 'O_E_NONE' 'Нет'),(New-Option 'O_E_PART' 'Частично'),(New-Option 'O_E_QA' 'Проверка качества пройдена'))),
    (New-Field 'F_EXECUTION' 'Исполнение' @((New-Option 'O_X_FREE' 'Свободно'),(New-Option 'O_X_ACTIVE' 'Активно'),(New-Option 'O_X_REVIEW' 'На проверке'),(New-Option 'O_X_QUEUE' 'В очереди'),(New-Option 'O_X_BLOCK' 'Заблокировано'),(New-Option 'O_X_RELEASED' 'Освобождено'))),
    (New-Field 'F_STATUS' 'Status' @((New-Option 'O_S_INBOX' 'Входящие'),(New-Option 'O_S_READY' 'Готово к работе'),(New-Option 'O_S_ACTIVE' 'В работе'),(New-Option 'O_S_QA' 'Проверка QA'),(New-Option 'O_S_BLOCK' 'Заблокировано'),(New-Option 'O_S_DONE' 'Готово')))
  )
  if($null -ne $script:MissingOption){
    foreach($field in $fields){$field.options=@($field.options|Where-Object{$_.name -cne $script:MissingOption})}
  }
  [pscustomobject]@{
    data=[pscustomobject]@{
      node=[pscustomobject]@{
        viewerCanUpdate=$script:CanUpdate
        fields=[pscustomobject]@{nodes=$fields}
      }
    }
  } | ConvertTo-Json -Depth 20 -Compress
}

function gh {
  $parts=@($args|ForEach-Object{[string]$_})
  $script:Calls+=,($parts)

  if($parts.Count -ge 2 -and $parts[0] -eq 'api' -and $parts[1] -eq 'user'){
    if($script:FailToken){$global:LASTEXITCODE=1;return 'denied'}
    $global:LASTEXITCODE=0
    return 'rassvetpublic-spec'
  }
  if($parts.Count -ge 2 -and $parts[0] -eq 'project' -and $parts[1] -eq 'view'){
    if($script:FailAccess){$global:LASTEXITCODE=1;return 'denied'}
    $global:LASTEXITCODE=0
    return '{"id":"PVT_PROJECT"}'
  }
  if($parts.Count -ge 2 -and $parts[0] -eq 'api' -and $parts[1] -eq 'graphql'){
    if($script:GraphQlFail){$global:LASTEXITCODE=1;return 'runtime failure'}
    $global:LASTEXITCODE=0
    return (ProjectSnapshotJson)
  }
  if($parts.Count -ge 2 -and $parts[0] -eq 'project' -and $parts[1] -eq 'item-list'){
    $global:LASTEXITCODE=0
    if($script:MissingItem){return '{"items":[]}' }
    return ([pscustomobject]@{items=@([pscustomobject]@{id='PVTI_ITEM';content=[pscustomobject]@{url=$Url}})} | ConvertTo-Json -Depth 10 -Compress)
  }
  if($parts.Count -ge 2 -and $parts[0] -eq 'project' -and $parts[1] -eq 'item-edit'){
    $fieldIndex=[Array]::IndexOf($parts,'--field-id')
    $fieldId=$parts[$fieldIndex+1]
    if($null -ne $script:FailFieldId -and $fieldId -ceq $script:FailFieldId){
      $global:LASTEXITCODE=1
      return $script:FailFieldText
    }
    $global:LASTEXITCODE=0
    return '{}'
  }
  throw "Неожиданный gh: $($parts -join ' ')"
}

function Reset-Probe{
  $script:Calls=@()
  $script:FailToken=$false
  $script:FailAccess=$false
  $script:CanUpdate=$true
  $script:GraphQlFail=$false
  $script:MissingItem=$false
  $script:MissingOption=$null
  $script:FailFieldId=$null
  $script:FailFieldText='fail'
  $script:SecretProbe='TEST_SECRET_VALUE_DO_NOT_PRINT'
  $env:GH_TOKEN=$script:SecretProbe
  $Url='https://github.com/rassvetpublic-spec/KAT9I_OS/issues/116'
  $State='ACTIVE'
  $Worker='ChatGPT'
  $QaWorker='AGY'
}

Reset-Probe
$env:GH_TOKEN=''
Assert-Code 'SECRET_MISSING' {Test-ProjectCredentialPreflight}
Assert-NoEdits 'SECRET_MISSING не должен выполнять Project mutation.'

Reset-Probe
$script:FailToken=$true
Assert-Code 'TOKEN_INVALID' {Test-ProjectCredentialPreflight}
Assert-NoEdits 'TOKEN_INVALID не должен выполнять Project mutation.'

Reset-Probe
$script:FailAccess=$true
Assert-Code 'PROJECT_ACCESS_DENIED' {Test-ProjectCredentialPreflight}
Assert-NoEdits 'PROJECT_ACCESS_DENIED не должен выполнять Project mutation.'

Reset-Probe
$script:CanUpdate=$false
Assert-Code 'PROJECT_WRITE_DENIED' {Test-ProjectCredentialPreflight}
Assert-NoEdits 'PROJECT_WRITE_DENIED preflight не должен выполнять Project mutation.'

Reset-Probe
$script:MissingOption='Частично'
Assert-Code 'PROJECT_SCHEMA_MISMATCH' {Test-ProjectCredentialPreflight}
Assert-NoEdits 'PROJECT_SCHEMA_MISMATCH не должен выполнять Project mutation.'

Reset-Probe
$script:GraphQlFail=$true
Assert-Code 'PROJECT_SYNC_FAILED' {Test-ProjectCredentialPreflight}
Assert-NoEdits 'PROJECT_SYNC_FAILED preflight не должен выполнять Project mutation.'

Reset-Probe
$preflight=Test-ProjectCredentialPreflight
Assert-Equal 'OK' $preflight.Code 'Позитивный preflight должен завершаться OK.'
Assert-NoEdits 'Позитивный preflight обязан быть read-only.'

Reset-Probe
$State='QUEUED'
$Worker='Codex'
$QaWorker='Antigravity (AGY)'
Sync-ProjectQueueState
$edits=@($script:Calls|Where-Object{$_.Count -ge 2 -and $_[0] -eq 'project' -and $_[1] -eq 'item-edit'})
Assert-Equal 5 $edits.Count 'QUEUED должен записать 5 полей.'
$fieldIds=@($edits|ForEach-Object{$_[[Array]::IndexOf($_,'--field-id')+1]})
Assert-Equal 'F_WORKER,F_QA,F_EVIDENCE,F_EXECUTION,F_STATUS' ($fieldIds -join ',') 'Статус должен оставаться последним commit-marker.'
foreach($call in $edits){
  Assert-True ($call -contains '--id') 'item-edit должен использовать item id.'
  Assert-True ($call -contains '--project-id') 'item-edit должен использовать project id.'
  Assert-True ($call -contains '--field-id') 'item-edit должен использовать field id.'
  Assert-True ($call -contains '--single-select-option-id') 'item-edit должен использовать option id.'
}
$qaCall=@($edits|Where-Object{$_[[Array]::IndexOf($_,'--field-id')+1] -ceq 'F_QA'})[0]
Assert-Equal 'O_QA_AGY' $qaCall[[Array]::IndexOf($qaCall,'--single-select-option-id')+1] 'Antigravity должен использовать AGY option id.'

Reset-Probe
$State='QUEUED'
$Worker='ChatGPT'
$QaWorker='AGY'
$script:FailFieldId='F_EVIDENCE'
$script:FailFieldText='HTTP 403 Forbidden'
Assert-Code 'PROJECT_WRITE_DENIED' {Sync-ProjectQueueState}
$written=@($script:Calls|Where-Object{$_.Count -ge 2 -and $_[1] -eq 'item-edit'}|ForEach-Object{$_[[Array]::IndexOf($_,'--field-id')+1]})
Assert-True (-not ($written -contains 'F_STATUS')) 'Статус не должен писаться после denied промежуточной mutation.'
Assert-True (-not ($written -contains 'F_EXECUTION')) 'Исполнение не должно писаться после denied Evidence mutation.'

Reset-Probe
$Url='https://github.com/other/repo/issues/1'
Assert-Code 'PROJECT_SYNC_FAILED' {
  try{Test-ProjectCredentialPreflight}catch{
    if($_.Exception.Message -match 'не является Issue/PR репозитория'){
      Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'Чужой URL блокируется до обращения к Project.'
    }
    throw
  }
}
Assert-Equal 0 $script:Calls.Count 'Чужой URL должен блокироваться до обращения к gh.'

Write-Host 'PASS: Project queue identity metadata, diagnostic preflight и fail-closed writes работают.'
