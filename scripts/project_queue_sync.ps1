param(
  [string]$Owner='rassvetpublic-spec',
  [string]$Repository='KAT9I_OS',
  [int]$ProjectNumber=2,
  [Parameter(Mandatory=$true)][string]$Url,
  [Parameter(Mandatory=$true)][ValidateSet('INBOX','READY','ACTIVE','QA','QUEUED','BLOCKED','DONE')][string]$State,
  [string]$Worker='ChatGPT',
  [string]$QaWorker='AGY',
  [switch]$LibraryMode
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

function Normalize-QaWorker([string]$Name){
  if([string]::IsNullOrWhiteSpace($Name)){throw 'QA Worker не может быть пустым.'}
  $value=$Name.Trim()
  if(@('AGY','Agy','Antigravity','Антигравити') -contains $value){return 'AGY'}
  return $value
}

function QueueProfile([string]$Name,[string]$WorkerName,[string]$QaName){
  $qaCanonical=Normalize-QaWorker $QaName
  switch($Name){
    'INBOX'   { return [ordered]@{'Доказательство'='Нет';'Исполнение'='Свободно';'Статус'='Входящие'} }
    'READY'   { return [ordered]@{'Доказательство'='Нет';'Исполнение'='Свободно';'Статус'='Готово к работе'} }
    'ACTIVE'  { return [ordered]@{'Исполнитель'=$WorkerName;'Проверяющий'=$qaCanonical;'Доказательство'='Частично';'Исполнение'='Активно';'Статус'='В работе'} }
    'QA'      { return [ordered]@{'Исполнитель'=$WorkerName;'Проверяющий'=$qaCanonical;'Доказательство'='Частично';'Исполнение'='На проверке';'Статус'='Проверка QA'} }
    'QUEUED'  { return [ordered]@{'Исполнитель'=$WorkerName;'Проверяющий'=$qaCanonical;'Доказательство'='Проверка качества пройдена';'Исполнение'='В очереди';'Статус'='Проверка QA'} }
    'BLOCKED' { return [ordered]@{'Исполнение'='Заблокировано';'Статус'='Заблокировано'} }
    'DONE'    { return [ordered]@{'Исполнение'='Освобождено';'Статус'='Готово'} }
  }
  throw "Неизвестное состояние очереди: $Name"
}

function Assert-ItemUrl{
  $ownerEsc=[regex]::Escape($Owner)
  $repoEsc=[regex]::Escape($Repository)
  if($Url -notmatch "^https://github\.com/$ownerEsc/$repoEsc/(issues|pull)/[0-9]+$"){
    throw "URL '$Url' не является Issue/PR репозитория $Owner/$Repository. Project queue не изменён."
  }
}

function Invoke-ProjectEdit([string]$Field,[string]$Value){
  $raw=& gh project item-edit $ProjectNumber --owner $Owner --url $Url --field $Field --value $Value --format json 2>&1
  if($LASTEXITCODE -ne 0){
    throw "Не удалось синхронизировать поле '$Field'='$Value' для $Url. Статус не продвигается до завершения вспомогательных полей; повторный запуск идемпотентно восстановит карточку. Ответ gh: $($raw -join ' ')"
  }
}

function Assert-ProjectAccess{
  $null=& gh project view $ProjectNumber --owner $Owner --format json 2>&1
  if($LASTEXITCODE -ne 0){
    throw "Нет write-доступа к GitHub Project #$ProjectNumber. Нужен credential со scope project; lifecycle не объявляется синхронизированным."
  }
}

function Sync-ProjectQueueState{
  Assert-ItemUrl
  Assert-ProjectAccess
  $profile=QueueProfile $State $Worker $QaWorker

  # GitHub Project меняет поля по одному. Вспомогательные поля записываются первыми,
  # а Статус — последним как видимый commit marker. При сбое повторный запуск идемпотентен.
  foreach($field in @('Исполнитель','Проверяющий','Доказательство','Исполнение')){
    if($profile.Contains($field)){Invoke-ProjectEdit $field ([string]$profile[$field])}
  }
  Invoke-ProjectEdit 'Статус' ([string]$profile['Статус'])
  Write-Host "Project queue synced: state=$State; url=$Url; worker=$Worker; qa=$(Normalize-QaWorker $QaWorker)"
}

if($LibraryMode){return}
if(-not(Get-Command gh -ErrorAction SilentlyContinue)){throw 'GitHub CLI (gh) не найден.'}
Sync-ProjectQueueState
