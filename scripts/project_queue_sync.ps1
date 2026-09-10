param(
  [string]$Owner='rassvetpublic-spec',
  [int]$ProjectNumber=2,
  [Parameter(Mandatory=$true)][string]$Url,
  [Parameter(Mandatory=$true)][ValidateSet('READY','ACTIVE','QA','QUEUED','BLOCKED','DONE')][string]$State,
  [string]$Worker='ChatGPT',
  [string]$QaWorker='Антигравити',
  [switch]$LibraryMode
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

function QueueProfile([string]$Name,[string]$WorkerName,[string]$QaName){
  switch($Name){
    'READY'   { return [ordered]@{'Доказательство'='Нет';'Исполнение'='Свободно';'Статус'='Готово к работе'} }
    'ACTIVE'  { return [ordered]@{'Исполнитель'=$WorkerName;'Проверяющий'=$QaName;'Доказательство'='Частично';'Исполнение'='Активно';'Статус'='В работе'} }
    'QA'      { return [ordered]@{'Исполнитель'=$WorkerName;'Проверяющий'=$QaName;'Доказательство'='Частично';'Исполнение'='На проверке';'Статус'='Проверка QA'} }
    'QUEUED'  { return [ordered]@{'Исполнитель'=$WorkerName;'Проверяющий'=$QaName;'Доказательство'='Проверка качества пройдена';'Исполнение'='В очереди';'Статус'='Проверка QA'} }
    'BLOCKED' { return [ordered]@{'Доказательство'='Частично';'Исполнение'='Заблокировано';'Статус'='Заблокировано'} }
    'DONE'    { return [ordered]@{'Исполнение'='Освобождено';'Статус'='Готово'} }
  }
  throw "Неизвестное состояние очереди: $Name"
}

function Invoke-ProjectEdit([string]$Field,[string]$Value){
  $raw=& gh project item-edit $ProjectNumber --owner $Owner --url $Url --field $Field --value $Value --format json 2>&1
  if($LASTEXITCODE -ne 0){
    throw "Не удалось синхронизировать поле '$Field'='$Value' для $Url. Project остаётся производным представлением; повторите синхронизацию. Ответ gh: $($raw -join ' ')"
  }
}

function Assert-ProjectAccess{
  $null=& gh project view $ProjectNumber --owner $Owner --format json 2>&1
  if($LASTEXITCODE -ne 0){
    throw "Нет write-доступа к GitHub Project #$ProjectNumber. Нужен credential со scope project; lifecycle не объявляется синхронизированным."
  }
}

function Sync-ProjectQueueState{
  Assert-ProjectAccess
  $profile=QueueProfile $State $Worker $QaWorker

  # Остальные поля меняются раньше, а Статус последним служит видимым commit marker карточки.
  foreach($field in @('Исполнитель','Проверяющий','Доказательство','Исполнение')){
    if($profile.Contains($field)){Invoke-ProjectEdit $field ([string]$profile[$field])}
  }
  Invoke-ProjectEdit 'Статус' ([string]$profile['Статус'])
  Write-Host "Project queue synced: state=$State; url=$Url; worker=$Worker; qa=$QaWorker"
}

if($LibraryMode){return}
if(-not(Get-Command gh -ErrorAction SilentlyContinue)){throw 'GitHub CLI (gh) не найден.'}
Sync-ProjectQueueState
