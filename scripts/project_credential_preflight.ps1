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

$syncPath=Join-Path $PSScriptRoot 'project_queue_sync.ps1'
. $syncPath -LibraryMode -Url $Url -State $State -Worker $Worker -QaWorker $QaWorker

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

function Invoke-PreflightGh([string[]]$Arguments,[string]$FailureCode,[string]$Purpose){
  $raw=@(& gh @Arguments 2>&1)
  if($LASTEXITCODE -ne 0){
    Fail-ProjectPreflight $FailureCode "$Purpose завершился ошибкой."
  }
  return (Convert-PreflightJson $raw $Purpose)
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
  $data=Invoke-PreflightGh @('api','graphql','-f',"query=$query",'-f',"id=$ProjectId") 'PROJECT_SYNC_FAILED' 'Чтение Project permissions/schema'
  if($null -ne (Get-PropertyValue $data 'errors')){
    Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'GitHub GraphQL вернул errors при чтении Project permissions/schema.'
  }
  $root=Get-PropertyValue (Get-PropertyValue $data 'data') 'node'
  if($null -eq $root){Fail-ProjectPreflight 'PROJECT_ACCESS_DENIED' "Project #$ProjectNumber недоступен для credential."}
  $canUpdate=Get-PropertyValue $root 'viewerCanUpdate'
  if($canUpdate -ne $true){
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

  $null=& gh api user --jq .login 2>$null
  if($LASTEXITCODE -ne 0){
    Fail-ProjectPreflight 'TOKEN_INVALID' 'GitHub отклонил credential; содержимое токена не выводится.'
  }

  $project=Invoke-PreflightGh @('project','view',"$ProjectNumber",'--owner',$Owner,'--format','json') 'PROJECT_ACCESS_DENIED' "Чтение Project #$ProjectNumber"
  $projectId=[string](Get-PropertyValue $project 'id')
  if([string]::IsNullOrWhiteSpace($projectId)){
    Fail-ProjectPreflight 'PROJECT_ACCESS_DENIED' "Project #$ProjectNumber не вернул GraphQL id."
  }

  $snapshot=Get-PreflightProjectSnapshot $projectId

  $items=Invoke-PreflightGh @('project','item-list',"$ProjectNumber",'--owner',$Owner,'--limit','1000','--format','json') 'PROJECT_SYNC_FAILED' 'Чтение Project items'
  $itemsProperty=$items.PSObject.Properties['items']
  if($null -eq $itemsProperty){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'Project item-list не вернул items.'}
  $matches=@(@($itemsProperty.Value)|Where-Object{[string](Get-PropertyValue (Get-PropertyValue $_ 'content') 'url') -ceq $Url})
  if($matches.Count -ne 1){Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' "Для $Url должна существовать ровно одна карточка Project."}

  $profile=QueueProfile $State $Worker $QaWorker
  foreach($field in $profile.Keys){
    $null=Resolve-PreflightBinding $snapshot.Fields $field ([string]$profile[$field])
  }

  return [pscustomobject]@{Code='OK';ProjectId=$projectId;ItemId=[string](Get-PropertyValue $matches[0] 'id')}
}

if($LibraryMode){return}
if(-not(Get-Command gh -ErrorAction SilentlyContinue)){
  Fail-ProjectPreflight 'PROJECT_SYNC_FAILED' 'GitHub CLI (gh) не найден.'
}
$result=Test-ProjectCredentialPreflight
Write-Host "KAT9I_PROJECT_PREFLIGHT=$($result.Code) | Project #$ProjectNumber доступен, write capability и schema подтверждены без mutation."
