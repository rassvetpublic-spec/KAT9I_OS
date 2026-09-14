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

# Dot-source дочернего script в PowerShell выполняется в текущем scope и может
# перезаписать одноимённые параметры. Сохраняем режим вызывающего preflight явно.
$preflightLibraryMode=[bool]$LibraryMode
$syncPath=Join-Path $PSScriptRoot 'project_queue_sync.ps1'
. $syncPath -Owner $Owner -Repository $Repository -ProjectNumber $ProjectNumber -LibraryMode -Url $Url -State $State -Worker $Worker -QaWorker $QaWorker

function Fail-ProjectPreflight([string]$Code,[string]$Message){
  throw "KAT9I_PROJECT_PREFLIGHT=$Code | $Message"
}

function Convert-PreflightJson([object[]]$Raw,[string]$Purpose){
  $text=($Raw -join "`n")
  if([string]::IsNullOrWhiteSpace($text)){
    Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "$Purpose вернул пустой ответ."
  }
  try{return ($text | ConvertFrom-Json -Depth 40)}
  catch{Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "$Purpose вернул некорректный JSON."}
}

function Test-ConfirmedTokenInvalid([string]$Text){
  return $Text -match '(?i)bad credentials|HTTP\s*401|authentication failed|requires authentication'
}

function Test-ConfirmedProjectDenied([string]$Text){
  return $Text -match '(?i)forbidden|resource not accessible|HTTP\s*403|could not resolve to a ProjectV2|project.*not found'
}

function Invoke-PreflightGh([string[]]$Arguments,[ValidateSet('AUTH','PROJECT_READ','RUNTIME')][string]$FailureKind,[string]$Purpose){
  $raw=@(& gh @Arguments 2>&1)
  if($LASTEXITCODE -ne 0){
    $text=($raw -join "`n")
    if($FailureKind -eq 'AUTH' -and (Test-ConfirmedTokenInvalid $text)){
      Fail-ProjectPreflight 'TOKEN_INVALID' 'GitHub подтвердил отказ credential; содержимое токена не выводится.'
    }
    if($FailureKind -eq 'PROJECT_READ' -and (Test-ConfirmedProjectDenied $text)){
      Fail-ProjectPreflight 'PROJECT_ACCESS_DENIED' "Credential аутентифицирован, но Project #$ProjectNumber недоступен."
    }
    Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "$Purpose завершился ошибкой, которую нельзя безопасно классифицировать точнее."
  }
  if($FailureKind -eq 'AUTH'){return $raw}
  return (Convert-PreflightJson $raw $Purpose)
}

function Assert-NoGraphQlErrors($Data,[string]$Purpose){
  $errors=Get-PropertyValue $Data 'errors'
  if($null -eq $errors){return}
  $errorText=($errors | ConvertTo-Json -Depth 20 -Compress)
  if(Test-ConfirmedProjectDenied $errorText){
    Fail-ProjectPreflight 'PROJECT_ACCESS_DENIED' "$Purpose: GitHub GraphQL запретил доступ к Project #$ProjectNumber."
  }
  Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "$Purpose: GitHub GraphQL вернул errors."
}

function Resolve-PreflightProjectId{
  $query=@'
query($login:String!,$number:Int!){
  user(login:$login){projectV2(number:$number){id}}
  organization(login:$login){projectV2(number:$number){id}}
}
'@
  $data=Invoke-PreflightGh @('api','graphql','-f',"query=$query",'-f',"login=$Owner",'-F',"number=$ProjectNumber") 'PROJECT_READ' "Разрешение Project #$ProjectNumber по owner"
  Assert-NoGraphQlErrors $data 'Разрешение Project owner'
  $root=Get-PropertyValue $data 'data'
  $ids=@()
  foreach($ownerNodeName in @('user','organization')){
    $ownerNode=Get-PropertyValue $root $ownerNodeName
    $projectNode=Get-PropertyValue $ownerNode 'projectV2'
    $candidate=[string](Get-PropertyValue $projectNode 'id')
    if(-not [string]::IsNullOrWhiteSpace($candidate)){$ids+=,$candidate}
  }
  $ids=@($ids|Select-Object -Unique)
  if($ids.Count -eq 0){Fail-ProjectPreflight 'PROJECT_ACCESS_DENIED' "Project #$ProjectNumber для owner '$Owner' не найден или недоступен."}
  if($ids.Count -gt 1){Fail-ProjectPreflight 'PROJECT_SCHEMA_MISMATCH' "Project #$ProjectNumber для owner '$Owner' разрешился неоднозначно."}
  return [string]$ids[0]
}

function Resolve-PreflightProjectItemId([string]$ProjectId){
  $query=@'
query($id:ID!,$after:String){
  node(id:$id){
    ... on ProjectV2{
      items(first:100,after:$after){
        nodes{
          id
          content{
            __typename
            ... on Issue{url}
            ... on PullRequest{url}
          }
        }
        pageInfo{hasNextPage endCursor}
      }
    }
  }
}
'@
  $matches=@()
  $after=''
  $seen=@{}
  do{
    $arguments=@('api','graphql','-f',"query=$query",'-f',"id=$ProjectId")
    if(-not [string]::IsNullOrWhiteSpace($after)){$arguments+=@('-f',"after=$after")}
    $data=Invoke-PreflightGh $arguments 'PROJECT_READ' 'Чтение Project items через GraphQL'
    Assert-NoGraphQlErrors $data 'Чтение Project items'
    $root=Get-PropertyValue (Get-PropertyValue $data 'data') 'node'
    $items=Get-PropertyValue $root 'items'
    if($null -eq $items){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'Project GraphQL не вернул items.'}
    foreach($item in @((Get-PropertyValue $items 'nodes'))){
      $content=Get-PropertyValue $item 'content'
      $itemUrl=[string](Get-PropertyValue $content 'url')
      if($itemUrl -ceq $Url){$matches+=,$item}
    }
    $pageInfo=Get-PropertyValue $items 'pageInfo'
    if($null -eq $pageInfo){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'Project GraphQL не вернул pageInfo.'}
    $hasNext=(Get-PropertyValue $pageInfo 'hasNextPage') -eq $true
    if($hasNext){
      $next=[string](Get-PropertyValue $pageInfo 'endCursor')
      if([string]::IsNullOrWhiteSpace($next)){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'Project pagination требует продолжение, но endCursor пуст.'}
      if($seen.ContainsKey($next)){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'Project pagination повторила endCursor; чтение остановлено fail-closed.'}
      $seen[$next]=$true
      $after=$next
    }
  }while($hasNext)

  if($matches.Count -eq 0){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "Карточка для $Url не найдена в Project #$ProjectNumber."}
  if($matches.Count -gt 1){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "Для $Url найдено несколько Project items; mutation запрещена."}
  $itemId=[string](Get-PropertyValue $matches[0] 'id')
  if([string]::IsNullOrWhiteSpace($itemId)){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "Карточка $Url не вернула item id."}
  return $itemId
}

function Get-PreflightProjectSnapshot([string]$ProjectId){
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
  $data=Invoke-PreflightGh @('api','graphql','-f',"query=$query",'-f',"id=$ProjectId") 'PROJECT_READ' 'Чтение Project permissions/schema'
  Assert-NoGraphQlErrors $data 'Чтение Project permissions/schema'
  $root=Get-PropertyValue (Get-PropertyValue $data 'data') 'node'
  if($null -eq $root){Fail-ProjectPreflight 'PROJECT_ACCESS_DENIED' "Project #$ProjectNumber недоступен для credential."}
  if((Get-PropertyValue $root 'viewerCanUpdate') -ne $true){
    Fail-ProjectPreflight 'PROJECT_WRITE_DENIED' "Credential может читать Project #$ProjectNumber, но viewerCanUpdate=false."
  }
  $fields=Get-PropertyValue $root 'fields'
  if($null -eq $fields){Fail-ProjectPreflight 'PROJECT_SCHEMA_MISMATCH' 'Project не вернул обязательные fields.'}
  $nodesProperty=$fields.PSObject.Properties['nodes']
  if($null -eq $nodesProperty){Fail-ProjectPreflight 'PROJECT_SCHEMA_MISMATCH' 'Project не вернул fields.nodes.'}
  return [pscustomobject]@{Fields=@($nodesProperty.Value);CanUpdate=$true}
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
  return [pscustomobject]@{FieldId=[string]$fieldMatches[0].id;OptionId=[string]$optionMatches[0].id}
}

function Test-ProjectCredentialPreflight{
  Assert-ItemUrl

  if([string]::IsNullOrWhiteSpace($env:GH_TOKEN)){
    Fail-ProjectPreflight 'SECRET_MISSING' 'Secret KAT9I_PROJECT_TOKEN не передан в workflow.'
  }

  $null=Invoke-PreflightGh @('api','user','--jq','.login') 'AUTH' 'Проверка GitHub credential'
  $projectId=Resolve-PreflightProjectId
  $snapshot=Get-PreflightProjectSnapshot $projectId
  $itemId=Resolve-PreflightProjectItemId $projectId

  $profile=QueueProfile $State $Worker $QaWorker
  foreach($field in $profile.Keys){
    $null=Resolve-PreflightBinding $snapshot.Fields $field ([string]$profile[$field])
  }

  return [pscustomobject]@{Code='OK';ProjectId=$projectId;ItemId=$itemId}
}

function Publish-ProjectPreflightOutputs($Result){
  if([string]::IsNullOrWhiteSpace($env:GITHUB_OUTPUT)){return}
  if($null -eq $Result){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'Нельзя опубликовать пустой preflight result.'}
  $projectId=[string](Get-PropertyValue $Result 'ProjectId')
  $itemId=[string](Get-PropertyValue $Result 'ItemId')
  if([string]::IsNullOrWhiteSpace($projectId) -or [string]::IsNullOrWhiteSpace($itemId)){
    Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'Preflight result не содержит exact ProjectId/ItemId для mutation handoff.'
  }
  Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "project_id=$projectId" -Encoding utf8
  Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "item_id=$itemId" -Encoding utf8
}

if($preflightLibraryMode){return}
if(-not(Get-Command gh -ErrorAction SilentlyContinue)){
  Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'GitHub CLI (gh) не найден.'
}
$result=Test-ProjectCredentialPreflight
Publish-ProjectPreflightOutputs $result
Write-Host "KAT9I_PROJECT_PREFLIGHT=OK | Project #$ProjectNumber доступен, write capability, schema и exact Project/Item IDs подтверждены без mutation."
