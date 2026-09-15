Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$scriptPath=Join-Path $PSScriptRoot '..' 'scripts' 'project_credential_preflight.ps1'

function Assert-True($Condition,[string]$Message){if(-not $Condition){throw $Message}}
function Assert-Equal($Expected,$Actual,[string]$Message){if($Expected -cne $Actual){throw "$Message Ожидалось='$Expected', фактически='$Actual'."}}

$global:Kat9iPreflightTestMode='OK'
$global:Kat9iPreflightTestCalls=@()
$global:Kat9iPreflightTestAllowSync=$false
$global:Kat9iPreflightTestSecret='SUPER_SECRET_DO_NOT_PRINT'
$env:GH_TOKEN=$global:Kat9iPreflightTestSecret

function New-Option([string]$Id,[string]$Name){[pscustomobject]@{id=$Id;name=$Name}}
function New-Field([string]$Id,[string]$Name,[object[]]$Options){[pscustomobject]@{__typename='ProjectV2SingleSelectField';id=$Id;name=$Name;options=$Options}}
function ProjectSnapshot([bool]$CanUpdate=$true,[string]$MissingOption=''){
  $fields=@(
    (New-Field 'F_WORKER' 'Исполнитель' @((New-Option 'OW1' 'ChatGPT'))),
    (New-Field 'F_QA' 'Проверяющий' @((New-Option 'OQ1' 'AGY'))),
    (New-Field 'F_EVIDENCE' 'Доказательство' @((New-Option 'OE1' 'Частично'))),
    (New-Field 'F_EXECUTION' 'Исполнение' @((New-Option 'OX1' 'Активно'))),
    (New-Field 'F_STATUS' 'Status' @((New-Option 'OS1' 'В работе')))
  )
  if($MissingOption){foreach($f in $fields){$f.options=@($f.options|Where-Object{$_.name -cne $MissingOption})}}
  [pscustomobject]@{data=[pscustomobject]@{node=[pscustomobject]@{viewerCanUpdate=$CanUpdate;fields=[pscustomobject]@{nodes=$fields}}}}
}

function gh {
  $parts=@($args|ForEach-Object{[string]$_})
  $global:Kat9iPreflightTestCalls+=,($parts)
  if($parts[0] -eq 'api' -and $parts[1] -eq 'user'){
    if($global:Kat9iPreflightTestMode -eq 'TOKEN_INVALID'){$global:LASTEXITCODE=1;return 'HTTP 401: Bad credentials'}
    if($global:Kat9iPreflightTestMode -eq 'AUTH_RUNTIME'){$global:LASTEXITCODE=1;return 'connection reset by peer'}
    $global:LASTEXITCODE=0;return 'rassvetpublic-spec'
  }
  if($parts[0] -eq 'project' -and $parts[1] -eq 'view'){
    if($global:Kat9iPreflightTestMode -eq 'ACCESS_DENIED'){$global:LASTEXITCODE=1;return 'HTTP 403: Resource not accessible'}
    if($global:Kat9iPreflightTestMode -eq 'PROJECT_RUNTIME'){$global:LASTEXITCODE=1;return 'gateway timeout'}
    $global:LASTEXITCODE=0;return '{"id":"PVT_PROJECT"}'
  }
  if($parts[0] -eq 'api' -and $parts[1] -eq 'graphql'){
    $global:LASTEXITCODE=0
    if($global:Kat9iPreflightTestMode -eq 'WRITE_DENIED'){return (ProjectSnapshot $false | ConvertTo-Json -Depth 20 -Compress)}
    if($global:Kat9iPreflightTestMode -eq 'SCHEMA_MISMATCH'){return (ProjectSnapshot $true 'Частично' | ConvertTo-Json -Depth 20 -Compress)}
    return (ProjectSnapshot $true | ConvertTo-Json -Depth 20 -Compress)
  }
  if($parts[0] -eq 'project' -and $parts[1] -eq 'item-list'){
    if($global:Kat9iPreflightTestMode -eq 'ITEM_RUNTIME'){$global:LASTEXITCODE=1;return 'gateway timeout'}
    $global:LASTEXITCODE=0
    return ([pscustomobject]@{items=@([pscustomobject]@{id='PVTI_ITEM';content=[pscustomobject]@{url='https://github.com/rassvetpublic-spec/KAT9I_OS/issues/116'}})} | ConvertTo-Json -Depth 10 -Compress)
  }
  if($parts.Count -gt 1 -and $parts[0] -eq 'project' -and $parts[1] -eq 'item-edit'){
    if(-not $global:Kat9iPreflightTestAllowSync){throw 'Preflight не должен выполнять mutation.'}
    $global:LASTEXITCODE=0;return '{}'
  }
  throw "Неожиданный gh вызов: $($parts -join ' ')"
}

. $scriptPath -LibraryMode -Url 'https://github.com/rassvetpublic-spec/KAT9I_OS/issues/116' -State ACTIVE -Worker ChatGPT -QaWorker AGY

function Invoke-Case([string]$Mode,[string]$ExpectedCode){
  $global:Kat9iPreflightTestMode=$Mode;$global:Kat9iPreflightTestCalls=@();$env:GH_TOKEN=$global:Kat9iPreflightTestSecret
  $message=''
  try{$null=Test-ProjectCredentialPreflight;throw 'Ожидалась ошибка preflight.'}catch{$message=$_.Exception.Message}
  Assert-True ($message -match "KAT9I_PROJECT_PREFLIGHT=$ExpectedCode") "Неверный код для $Mode. Сообщение: $message"
  Assert-True ($message -notmatch [regex]::Escape($global:Kat9iPreflightTestSecret)) "Secret попал в сообщение для $Mode."
  Assert-True (-not (@($global:Kat9iPreflightTestCalls|Where-Object{$_.Count -gt 1 -and $_[0] -eq 'project' -and $_[1] -eq 'item-edit'}).Count)) "Preflight выполнил mutation для $Mode."
}

$global:Kat9iPreflightTestCalls=@();$env:GH_TOKEN=''
$message=''
try{$null=Test-ProjectCredentialPreflight;throw 'Ожидалась SECRET_MISSING.'}catch{$message=$_.Exception.Message}
Assert-True ($message -match 'KAT9I_PROJECT_PREFLIGHT=SECRET_MISSING') 'SECRET_MISSING не распознан.'
Assert-Equal 0 $global:Kat9iPreflightTestCalls.Count 'При отсутствии secret gh не должен вызываться.'

Invoke-Case 'TOKEN_INVALID' 'TOKEN_INVALID'
Invoke-Case 'AUTH_RUNTIME' 'PROJECT_SYNC_FAILED'
Invoke-Case 'ACCESS_DENIED' 'PROJECT_ACCESS_DENIED'
Invoke-Case 'PROJECT_RUNTIME' 'PROJECT_SYNC_FAILED'
Invoke-Case 'WRITE_DENIED' 'PROJECT_WRITE_DENIED'
Invoke-Case 'SCHEMA_MISMATCH' 'PROJECT_SCHEMA_MISMATCH'
Invoke-Case 'ITEM_RUNTIME' 'PROJECT_SYNC_FAILED'

$global:Kat9iPreflightTestMode='TOKEN_INVALID';$global:Kat9iPreflightTestCalls=@();$env:GH_TOKEN=$global:Kat9iPreflightTestSecret
try{$null=Test-ProjectCredentialPreflight}catch{}
$global:Kat9iPreflightTestMode='OK';$global:Kat9iPreflightTestCalls=@()
$result=Test-ProjectCredentialPreflight
Assert-Equal 'OK' $result.Code 'После исправления credential повторный preflight должен пройти.'
Assert-Equal 'PVTI_ITEM' $result.ItemId 'Позитивный preflight должен разрешить существующую карточку.'
Assert-True (-not (@($global:Kat9iPreflightTestCalls|Where-Object{$_.Count -gt 1 -and $_[0] -eq 'project' -and $_[1] -eq 'item-edit'}).Count)) 'Позитивный preflight не должен мутировать Project.'

# Проверяем реальные точки входа, а не только функцию из LibraryMode.
# GitHub заменён только на границе gh: реальные карточки тест не изменяет.
$tempDir=Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
$null=New-Item -ItemType Directory -Path $tempDir
$handoffPath=Join-Path $tempDir 'project-preflight.json'
$syncScript=Join-Path $PSScriptRoot '..' 'scripts' 'project_queue_sync.ps1'
$diagnosticScript=Join-Path $PSScriptRoot '..' 'scripts' 'project_preflight_diagnostic.ps1'
try {
  $global:Kat9iPreflightTestCalls=@()
  & $scriptPath -Url 'https://github.com/rassvetpublic-spec/KAT9I_OS/issues/116' -State ACTIVE -Worker ChatGPT -QaWorker AGY -OutputPath $handoffPath
  Assert-True (Test-Path -LiteralPath $handoffPath -PathType Leaf) 'Обычный запуск preflight не создал файл.'
  $handoff=Get-Content -LiteralPath $handoffPath -Raw | ConvertFrom-Json
  Assert-Equal 'PVTI_ITEM' $handoff.ItemId 'Файл должен содержать разрешённую карточку.'
  & $diagnosticScript -Path $handoffPath
  $global:Kat9iPreflightTestCalls=@();$global:Kat9iPreflightTestAllowSync=$true
  & $syncScript -Url $handoff.Url -State ACTIVE -Worker ChatGPT -QaWorker AGY -PreflightPath $handoffPath
  $writes=@($global:Kat9iPreflightTestCalls|Where-Object{$_[0] -eq 'project' -and $_[1] -eq 'item-edit'})
  Assert-Equal 5 $writes.Count 'Sync должен записать все пять полей ACTIVE.'
  Assert-True ($writes[-1] -contains 'F_STATUS') 'Статус должен записываться последним.'
  Assert-Equal 0 (@($global:Kat9iPreflightTestCalls|Where-Object{$_[0] -eq 'project' -and $_[1] -in @('view','item-list')}).Count) 'Sync должен использовать файл, без повторного поиска карточки.'
  $global:Kat9iPreflightTestCalls=@()
  $failed=$false
  try { & $syncScript -Url $handoff.Url -State ACTIVE -PreflightPath (Join-Path $tempDir 'missing.json') }
  catch { $failed=$true }
  Assert-True $failed 'Отсутствующий файл должен остановить sync.'
  Assert-Equal 0 $global:Kat9iPreflightTestCalls.Count 'Отсутствующий файл должен блокировать любые gh-вызовы.'
} finally {
  $global:Kat9iPreflightTestAllowSync=$false
  Remove-Item -LiteralPath $tempDir -Recurse -Force
}

Write-Host 'PASS: Project credential preflight diagnostics'
