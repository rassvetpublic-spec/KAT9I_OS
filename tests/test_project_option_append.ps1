Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$scriptPath=Join-Path $PSScriptRoot '..' 'scripts' 'configure_project.ps1'
. $scriptPath -LibraryMode

function WorkerDefs {
  @(
    (Opt 'ChatGPT' 'GREEN' 'ChatGPT.'),
    (Opt 'AGY' 'BLUE' 'AGY.'),
    (Opt 'Codex' 'PURPLE' 'Codex.'),
    (Opt 'Антигравити' 'PINK' 'Независимый QA Worker Антигравити.' @('Антигравити','Antigravity')),
    (Opt 'Человек' 'ORANGE' 'Человек.' @('Человек','Human')),
    (Opt 'Другой' 'GRAY' 'Другой исполнитель.' @('Другой','Other'))
  )
}

function ExistingOption([string]$Id,[string]$Name,[string]$Color='GRAY',[string]$Description='x'){
  [pscustomobject]@{id=$Id;name=$Name;color=$Color;description=$Description}
}

$script:Field=$null
$script:Mutations=0
$script:CapturedOptions=@()
function Snapshot {
  [pscustomobject]@{
    user=[pscustomobject]@{
      projectV2=[pscustomobject]@{
        id='PROJECT'
        fields=[pscustomobject]@{nodes=@($script:Field)}
      }
    }
  }
}
function Gql {
  param([string]$Query,[hashtable]$Variables)
  if($Query -notmatch 'updateProjectV2Field'){throw 'Неожиданный GraphQL.'}
  $script:Mutations++
  $script:CapturedOptions=@($Variables.input.singleSelectOptions)
  $after=@()
  $newIndex=1
  foreach($o in $script:CapturedOptions){
    $idProperty=$o.PSObject.Properties['id']
    $id=if($null -ne $idProperty){[string]$idProperty.Value}else{"NEW$newIndex";$newIndex++}
    $after+=ExistingOption $id ([string]$o.name) ([string]$o.color) ([string]$o.description)
  }
  $script:Field=[pscustomobject]@{id='WORKERS';name='Проверяющий';__typename='ProjectV2SingleSelectField';options=@($after)}
  [pscustomobject]@{data=[pscustomobject]@{updateProjectV2Field=[pscustomobject]@{projectV2Field=$script:Field}}}
}

function Reset-GoodField {
  $script:Mutations=0
  $script:CapturedOptions=@()
  $script:Field=[pscustomobject]@{
    id='WORKERS';name='Проверяющий';__typename='ProjectV2SingleSelectField';options=@(
      (ExistingOption 'O1' 'ChatGPT' 'GREEN' 'ChatGPT.'),
      (ExistingOption 'O2' 'AGY' 'BLUE' 'AGY.'),
      (ExistingOption 'O3' 'Codex' 'PURPLE' 'Codex.'),
      (ExistingOption 'O4' 'Человек' 'ORANGE' 'Человек.'),
      (ExistingOption 'O5' 'Другой' 'GRAY' 'Другой исполнитель.')
    )
  }
}

Reset-GoodField
EnsureSelect 'Проверяющий' @('Проверяющий','QA Worker') (WorkerDefs)
if($script:Mutations -ne 1){throw "Ожидалась одна mutation для safe append, получено $($script:Mutations)."}
if($script:CapturedOptions.Count -ne 6){throw 'Safe append должен передать 5 существующих + 1 новое значение.'}
foreach($pair in @(@('O1','ChatGPT'),@('O2','AGY'),@('O3','Codex'),@('O4','Человек'),@('O5','Другой'))){
  $match=@($script:CapturedOptions|Where-Object{$_.PSObject.Properties['id'] -and $_.id -ceq $pair[0] -and $_.name -ceq $pair[1]})
  if($match.Count -ne 1){throw "Не сохранён option ID $($pair[0]) для $($pair[1])."}
}
$new=@($script:CapturedOptions|Where-Object{$_.name -ceq 'Антигравити'})
if($new.Count -ne 1){throw 'Новое значение Антигравити не добавлено ровно один раз.'}
if($null -ne $new[0].PSObject.Properties['id']){throw 'Новое значение не должно притворяться существующим option ID.'}

Reset-GoodField
$script:Field.options[1].id=''
$failed=$false
try{EnsureSelect 'Проверяющий' @('Проверяющий','QA Worker') (WorkerDefs)}catch{$failed=$true;if($_.Exception.Message -notmatch 'без option ID'){throw}}
if(-not $failed){throw 'Существующее значение без option ID должно блокировать safe append.'}
if($script:Mutations -ne 0){throw 'При отсутствующем старом option ID mutation запрещена.'}

Reset-GoodField
$script:Field.options+=ExistingOption 'O6' 'Antigravity' 'PINK' 'legacy alias'
$failed=$false
try{EnsureSelect 'Проверяющий' @('Проверяющий','QA Worker') (WorkerDefs)}catch{$failed=$true;if($_.Exception.Message -notmatch 'требует изменения option ID'){throw}}
if(-not $failed){throw 'Legacy alias Antigravity должен требовать явную миграцию, а не переименование.'}
if($script:Mutations -ne 0){throw 'Legacy option migration не должна выполнять mutation.'}

Write-Host 'PASS: Антигравити добавляется без смены существующих option ID; небезопасная миграция fail-closed.'
