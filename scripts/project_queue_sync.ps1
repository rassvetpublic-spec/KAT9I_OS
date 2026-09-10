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
  if(@('AGY','Agy','Antigravity','Антигравити') -contains $value){return 'AGY'}
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

function Invoke-GhJson{
  param(
    [Parameter(Mandatory=$true)][string[]]$Arguments,
    [Parameter(Mandatory=$true)][string]$Purpose
  )
  $raw=& gh @Arguments 2>&1
  if($LASTEXITCODE -ne 0){
    throw "$Purpose завершился ошибкой. Ответ gh: $($raw -join ' ')"
  }
  $text=($raw -join "`n")
  if([string]::IsNullOrWhiteSpace($text)){throw "$Purpose вернул пустой JSON."}
  try{return ($text | ConvertFrom-Json -Depth 40)}
  catch{throw "$Purpose вернул некорректный JSON."}
}

function Assert-ProjectAccess{
  $project=Invoke-GhJson -Arguments @('project','view',"$ProjectNumber",'--owner',$Owner,'--format','json') -Purpose "Чтение Project #$ProjectNumber"
  $projectId=[string](Get-PropertyValue $project 'id')
  if([string]::IsNullOrWhiteSpace($projectId)){
    throw "Project #$ProjectNumber не вернул GraphQL id; lifecycle не синхронизирован."
  }
  return $project
}

function Resolve-ProjectItemId{
  $data=Invoke-GhJson -Arguments @('project','item-list',"$ProjectNumber",'--owner',$Owner,'--limit','1000','--format','json') -Purpose 'Чтение Project items'
  $itemsProperty=$data.PSObject.Properties['items']
  if($null -eq $itemsProperty){throw 'Project item-list не вернул items; lifecycle не синхронизирован.'}
  $items=@($itemsProperty.Value)
  $matches=@()
  foreach($item in $items){
    $content=Get-PropertyValue $item 'content'
    $itemUrl=[string](Get-PropertyValue $content 'url')
    if($itemUrl -ceq $Url){$matches+=,$item}
  }
  if($matches.Count -eq 0){throw "Карточка для $Url не найдена в Project #$ProjectNumber. Добавление/редактирование остановлено fail-closed."}
  if($matches.Count -gt 1){throw "Для $Url найдено несколько Project items; редактирование остановлено fail-closed."}
  $itemId=[string](Get-PropertyValue $matches[0] 'id')
  if([string]::IsNullOrWhiteSpace($itemId)){throw "Карточка $Url не вернула item id."}
  return $itemId
}

function Get-ProjectSelectFields([string]$ProjectId){
  $query=@'
query($id:ID!){
  node(id:$id){
    ... on ProjectV2{
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
  $data=Invoke-GhJson -Arguments @('api','graphql','-f',"query=$query",'-f',"id=$ProjectId") -Purpose 'Чтение Project field IDs'
  $errors=Get-PropertyValue $data 'errors'
  if($null -ne $errors){throw 'GitHub GraphQL вернул errors при чтении Project fields.'}
  $root=Get-PropertyValue (Get-PropertyValue $data 'data') 'node'
  $fieldsProperty=(Get-PropertyValue $root 'fields').PSObject.Properties['nodes']
  if($null -eq $fieldsProperty){throw 'Project GraphQL не вернул fields.'}
  return @($fieldsProperty.Value)
}

function Resolve-SelectBinding($Fields,[string]$Field,[string]$Value){
  $aliases=if($Field -ceq 'Статус'){@('Статус','Status')}else{@($Field)}
  $fieldMatches=@($Fields|Where-Object{
    $_.__typename -eq 'ProjectV2SingleSelectField' -and $aliases -contains $_.name
  })
  if($fieldMatches.Count -eq 0){throw "Single-select поле '$Field' не найдено; Project не изменён."}
  if($fieldMatches.Count -gt 1){throw "Поле '$Field' неоднозначно; Project не изменён."}
  $fieldNode=$fieldMatches[0]
  $optionMatches=@(@($fieldNode.options)|Where-Object{$_.name -ceq $Value})
  if($optionMatches.Count -eq 0){throw "Значение '$Value' не найдено в поле '$Field'; Project не изменён."}
  if($optionMatches.Count -gt 1){throw "Значение '$Value' неоднозначно в поле '$Field'; Project не изменён."}
  return [pscustomobject]@{
    Field=$Field
    Value=$Value
    FieldId=[string]$fieldNode.id
    OptionId=[string]$optionMatches[0].id
  }
}

function Invoke-ProjectEdit([string]$ProjectId,[string]$ItemId,$Binding){
  $raw=& gh project item-edit --id $ItemId --project-id $ProjectId --field-id $Binding.FieldId --single-select-option-id $Binding.OptionId 2>&1
  if($LASTEXITCODE -ne 0){
    throw "Не удалось синхронизировать поле '$($Binding.Field)'='$($Binding.Value)' для $Url. Статус не продвигается до завершения вспомогательных полей; повторный запуск идемпотентно восстановит карточку. Ответ gh: $($raw -join ' ')"
  }
}

function Sync-ProjectQueueState{
  Assert-ItemUrl
  $project=Assert-ProjectAccess
  $projectId=[string](Get-PropertyValue $project 'id')
  $itemId=Resolve-ProjectItemId
  $profile=QueueProfile $State $Worker $QaWorker
  $fields=Get-ProjectSelectFields $projectId

  # Все ID и option ID разрешаются до первой записи. Это не даёт частично
  # продвинуть stage из-за неизвестного поля/значения.
  $bindings=[ordered]@{}
  foreach($field in $profile.Keys){
    $bindings[$field]=Resolve-SelectBinding $fields $field ([string]$profile[$field])
  }

  # Вспомогательные поля — первыми, Статус — последним как commit marker стадии.
  foreach($field in @('Исполнитель','Проверяющий','Доказательство','Исполнение')){
    if($bindings.Contains($field)){Invoke-ProjectEdit $projectId $itemId $bindings[$field]}
  }
  Invoke-ProjectEdit $projectId $itemId $bindings['Статус']
  Write-Host "Project queue synced: state=$State; url=$Url; worker=$Worker; qa=$(Normalize-QaWorker $QaWorker)"
}

if($LibraryMode){return}
if(-not(Get-Command gh -ErrorAction SilentlyContinue)){throw 'GitHub CLI (gh) не найден.'}
Sync-ProjectQueueState
