param(
  [string]$Owner='rassvetpublic-spec',
  [string]$Repository='KAT9I_OS',
  [int]$ProjectNumber=2,
  [Parameter(Mandatory=$true)][string]$Url,
  [Parameter(Mandatory=$true)][ValidateSet('INBOX','READY','ACTIVE','QA','QUEUED','BLOCKED','DONE')][string]$State,
  [string]$Worker='',
  [string]$QaWorker='',
  [switch]$LibraryMode
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

function Get-PropertyValue($Object,[string]$Name){
  if($null -eq $Object){return $null}
  $property=$Object.PSObject.Properties[$Name]
  if($null -eq $property){return $null}
  return $property.Value
}

function Normalize-QaWorker([string]$Name){
  if([string]::IsNullOrWhiteSpace($Name)){return ''}
  $value=$Name.Trim()
  if(@('AGY','Agy','Antigravity','Антигравити','Antigravity (AGY)','Антигравити (AGY)') -contains $value){return 'AGY'}
  return $value
}

function QueueProfile([string]$Name,[string]$WorkerName,[string]$QaName){
  $profile=[ordered]@{}
  $qaCanonical=Normalize-QaWorker $QaName
  switch($Name){
    'INBOX' {
      $profile['Доказательство']='Нет'
      $profile['Исполнение']='Свободно'
      $profile['Статус']='Входящие'
    }
    'READY' {
      $profile['Доказательство']='Нет'
      $profile['Исполнение']='Свободно'
      $profile['Статус']='Готово к работе'
    }
    'ACTIVE' {
      if(-not [string]::IsNullOrWhiteSpace($WorkerName)){$profile['Исполнитель']=$WorkerName.Trim()}
      if(-not [string]::IsNullOrWhiteSpace($qaCanonical)){$profile['Проверяющий']=$qaCanonical}
      $profile['Доказательство']='Частично'
      $profile['Исполнение']='Активно'
      $profile['Статус']='В работе'
    }
    'QA' {
      if(-not [string]::IsNullOrWhiteSpace($WorkerName)){$profile['Исполнитель']=$WorkerName.Trim()}
      if(-not [string]::IsNullOrWhiteSpace($qaCanonical)){$profile['Проверяющий']=$qaCanonical}
      $profile['Доказательство']='Частично'
      $profile['Исполнение']='На проверке'
      $profile['Статус']='Проверка QA'
    }
    'QUEUED' {
      if(-not [string]::IsNullOrWhiteSpace($WorkerName)){$profile['Исполнитель']=$WorkerName.Trim()}
      if(-not [string]::IsNullOrWhiteSpace($qaCanonical)){$profile['Проверяющий']=$qaCanonical}
      $profile['Доказательство']='Проверка качества пройдена'
      $profile['Исполнение']='В очереди'
      $profile['Статус']='Проверка QA'
    }
    'BLOCKED' {
      $profile['Исполнение']='Заблокировано'
      $profile['Статус']='Заблокировано'
    }
    'DONE' {
      $profile['Исполнение']='Освобождено'
      $profile['Статус']='Готово'
    }
    default { throw "Неизвестное состояние очереди: $Name" }
  }
  return $profile
}

function Assert-ItemUrl{
  $ownerEsc=[regex]::Escape($Owner)
  $repoEsc=[regex]::Escape($Repository)
  if($Url -notmatch "^https://github\.com/$ownerEsc/$repoEsc/(issues|pull)/[0-9]+$"){
    throw "URL '$Url' не является Issue/PR репозитория $Owner/$Repository. Project queue не изменён."
  }
}

function Fail-ProjectPreflight([string]$Code,[string]$Message){
  throw "KAT9I_PROJECT_PREFLIGHT=$Code | $Message"
}

function Convert-ProjectJson([object[]]$Raw,[string]$Purpose){
  $text=($Raw -join "`n")
  if([string]::IsNullOrWhiteSpace($text)){
    Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "$Purpose вернул пустой ответ."
  }
  try{return ($text | ConvertFrom-Json -Depth 40)}
  catch{Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "$Purpose вернул некорректный JSON."}
}

function Invoke-ProjectRead([string[]]$Arguments,[string]$FailureCode,[string]$Purpose){
  $raw=@(& gh @Arguments 2>&1)
  if($LASTEXITCODE -ne 0){
    Fail-ProjectPreflight $FailureCode "$Purpose завершился ошибкой."
  }
  return (Convert-ProjectJson $raw $Purpose)
}

function Get-ProjectPreflightSnapshot([string]$ProjectId){
  $query=@'
query($id:ID!){
  node(id:$id){
    ... on ProjectV2{
      viewerCanUpdate
      fields(first:100){
        nodes{
          __typename
          ... on ProjectV2SingleSelectField{
            id
            name
            options{id name}
          }
        }
      }
    }
  }
}
'@
  $data=Invoke-ProjectRead @('api','graphql','-f',"query=$query",'-f',"id=$ProjectId") 'PROJECT_SYNC_FAILED' 'Чтение Project permissions/schema'
  if($null -ne (Get-PropertyValue $data 'errors')){
    Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'GitHub GraphQL вернул errors при чтении Project permissions/schema.'
  }
  $root=Get-PropertyValue (Get-PropertyValue $data 'data') 'node'
  if($null -eq $root){Fail-ProjectPreflight 'PROJECT_ACCESS_DENIED' "Project #$ProjectNumber недоступен для credential."}
  if((Get-PropertyValue $root 'viewerCanUpdate') -ne $true){
    Fail-ProjectPreflight 'PROJECT_WRITE_DENIED' "Credential может читать Project #$ProjectNumber, но viewerCanUpdate=false."
  }
  $fields=Get-PropertyValue $root 'fields'
  if($null -eq $fields){Fail-ProjectPreflight 'PROJECT_SCHEMA_MISMATCH' 'Project не вернул обязательные fields.'}
  $nodesProperty=$fields.PSObject.Properties['nodes']
  if($null -eq $nodesProperty){Fail-ProjectPreflight 'PROJECT_SCHEMA_MISMATCH' 'Project не вернул fields.nodes.'}
  return @($nodesProperty.Value)
}

function Resolve-PreflightBinding($Fields,[string]$Field,[string]$Value){
  $aliases=if($Field -ceq 'Статус'){@('Статус','Status')}else{@($Field)}
  $fieldMatches=@($Fields|Where-Object{
    $_.__typename -eq 'ProjectV2SingleSelectField' -and $aliases -contains $_.name
  })
  if($fieldMatches.Count -ne 1){
    Fail-ProjectPreflight 'PROJECT_SCHEMA_MISMATCH' "Single-select поле '$Field' отсутствует или неоднозначно."
  }
  $optionMatches=@(@($fieldMatches[0].options)|Where-Object{$_.name -ceq $Value})
  if($optionMatches.Count -ne 1){
    Fail-ProjectPreflight 'PROJECT_SCHEMA_MISMATCH' "Значение '$Value' поля '$Field' отсутствует или неоднозначно."
  }
  return [pscustomobject]@{
    Field=$Field
    Value=$Value
    FieldId=[string]$fieldMatches[0].id
    OptionId=[string]$optionMatches[0].id
  }
}

function Test-ProjectCredentialPreflight{
  Assert-ItemUrl

  if([string]::IsNullOrWhiteSpace($env:GH_TOKEN)){
    Fail-ProjectPreflight 'SECRET_MISSING' 'Secret KAT9I_PROJECT_TOKEN не передан в workflow.'
  }

  $null=& gh api user --jq .login 2>$null
  if($LASTEXITCODE -ne 0){
    Fail-ProjectPreflight 'TOKEN_INVALID' 'GitHub отклонил credential; содержимое токена не выводится.'
  }

  $project=Invoke-ProjectRead @('project','view',"$ProjectNumber",'--owner',$Owner,'--format','json') 'PROJECT_ACCESS_DENIED' "Чтение Project #$ProjectNumber"
  $projectId=[string](Get-PropertyValue $project 'id')
  if([string]::IsNullOrWhiteSpace($projectId)){
    Fail-ProjectPreflight 'PROJECT_ACCESS_DENIED' "Project #$ProjectNumber не вернул GraphQL id."
  }

  $fields=Get-ProjectPreflightSnapshot $projectId
  $items=Invoke-ProjectRead @('project','item-list',"$ProjectNumber",'--owner',$Owner,'--limit','1000','--format','json') 'PROJECT_SYNC_FAILED' 'Чтение Project items'
  $itemsProperty=$items.PSObject.Properties['items']
  if($null -eq $itemsProperty){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'Project item-list не вернул items.'}
  $matches=@(@($itemsProperty.Value)|Where-Object{[string](Get-PropertyValue (Get-PropertyValue $_ 'content') 'url') -ceq $Url})
  if($matches.Count -ne 1){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "Для $Url должна существовать ровно одна карточка Project."}
  $itemId=[string](Get-PropertyValue $matches[0] 'id')
  if([string]::IsNullOrWhiteSpace($itemId)){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "Карточка $Url не вернула item id."}

  $profile=QueueProfile $State $Worker $QaWorker
  $bindings=[ordered]@{}
  foreach($field in $profile.Keys){
    $bindings[$field]=Resolve-PreflightBinding $fields $field ([string]$profile[$field])
  }

  return [pscustomobject]@{
    Code='OK'
    ProjectId=$projectId
    ItemId=$itemId
    Bindings=$bindings
  }
}

function Invoke-ProjectEdit([string]$ProjectId,[string]$ItemId,$Binding){
  $raw=@(& gh project item-edit --id $ItemId --project-id $ProjectId --field-id $Binding.FieldId --single-select-option-id $Binding.OptionId 2>&1)
  if($LASTEXITCODE -ne 0){
    $text=($raw -join ' ')
    if($text -match '(?i)forbidden|permission|resource not accessible|HTTP 403'){
      Fail-ProjectPreflight 'PROJECT_WRITE_DENIED' "GitHub отклонил Project mutation поля '$($Binding.Field)'."
    }
    Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "Не удалось синхронизировать поле '$($Binding.Field)'='$($Binding.Value)'; повторный запуск идемпотентно восстановит карточку."
  }
}

function Sync-ProjectQueueState{
  $preflight=Test-ProjectCredentialPreflight
  Write-Host "KAT9I_PROJECT_PREFLIGHT=OK | Project #$ProjectNumber read/write/schema подтверждены без mutation."

  foreach($field in @('Исполнитель','Проверяющий','Доказательство','Исполнение')){
    if($preflight.Bindings.Contains($field)){
      Invoke-ProjectEdit $preflight.ProjectId $preflight.ItemId $preflight.Bindings[$field]
    }
  }
  Invoke-ProjectEdit $preflight.ProjectId $preflight.ItemId $preflight.Bindings['Статус']
  Write-Host "Project queue synced: state=$State; url=$Url; worker=$Worker; qa=$(Normalize-QaWorker $QaWorker)"
}

if($LibraryMode){return}
if(-not(Get-Command gh -ErrorAction SilentlyContinue)){
  Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'GitHub CLI (gh) не найден.'
}
Sync-ProjectQueueState
