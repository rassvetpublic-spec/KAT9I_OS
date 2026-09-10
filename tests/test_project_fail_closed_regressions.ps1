Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$scriptPath=Join-Path $PSScriptRoot '..' 'scripts' 'configure_project.ps1'
. $scriptPath -LibraryMode

$tokens=$null
$parseErrors=$null
$productionAst=[System.Management.Automation.Language.Parser]::ParseFile($scriptPath,[ref]$tokens,[ref]$parseErrors)
if(@($parseErrors).Count -gt 0){
  throw "Production configure_project.ps1 не разбирается PowerShell Parser: $((@($parseErrors)|ForEach-Object{$_.Message}) -join '; ')"
}
$entrypointCommands=@($productionAst.FindAll({
  param($node)
  if($node -isnot [System.Management.Automation.Language.CommandAst]){return $false}
  return $node.GetCommandName() -ceq 'Invoke-ProjectConfiguration'
},$true))
if($entrypointCommands.Count -ne 1){
  throw "В production-скрипте должна быть ровно одна команда Invoke-ProjectConfiguration; найдено $($entrypointCommands.Count)."
}
$applyExpressions=@($entrypointCommands[0].CommandElements|Where-Object{$_ -is [System.Management.Automation.Language.ScriptBlockExpressionAst]})
if($applyExpressions.Count -ne 1){throw 'Не найдено фактическое production-тело Apply.'}
$script:ProductionApply=$applyExpressions[0].ScriptBlock.GetScriptBlock()

$script:MockViews=@()
$script:MockFields=@()
$script:GqlCalls=0
$script:RestWrites=0
$script:ItemAddCalls=0
$script:IssueListExitCode=0
$script:PrListExitCode=0

function New-View([string]$Name,[string]$Id,[string]$Layout,[string]$Filter){
  [pscustomobject]@{id=$Id;name=$Name;layout=$Layout;filter=$Filter}
}

function New-CanonicalViews {
  @(
    (New-View '00 — Все задачи' 'C0' 'TABLE_LAYOUT' 'is:open'),
    (New-View '01 — Готово к работе' 'C1' 'TABLE_LAYOUT' 'is:open Статус:"Готово к работе" -Исполнение:"Заблокировано"'),
    (New-View '02 — В работе' 'C2' 'BOARD_LAYOUT' 'is:open Статус:"В работе"'),
    (New-View '03 — Проверка' 'C3' 'BOARD_LAYOUT' 'is:open Статус:"Проверка QA"'),
    (New-View '04 — Заблокировано' 'C4' 'TABLE_LAYOUT' 'is:open Статус:"Заблокировано"')
  )
}

function New-StatusField([object[]]$Options=@()){
  [pscustomobject]@{
    id='STATUS'
    name='Статус'
    __typename='ProjectV2SingleSelectField'
    options=@($Options)
  }
}

function Reset-State {
  $script:MockViews=@(New-CanonicalViews)
  $script:MockFields=@(New-StatusField)
  $script:GqlCalls=0
  $script:RestWrites=0
  $script:ItemAddCalls=0
  $script:IssueListExitCode=0
  $script:PrListExitCode=0
  $script:ProjectPreflightOnly=$false
}

function Snapshot {
  [pscustomobject]@{
    user=[pscustomobject]@{
      projectV2=[pscustomobject]@{
        id='PROJECT'
        title='KAT9I_OS — разработка'
        repositories=[pscustomobject]@{nodes=@([pscustomobject]@{id='REPO';nameWithOwner='rassvetpublic-spec/KAT9I_OS'})}
        fields=[pscustomobject]@{nodes=@($script:MockFields)}
        views=[pscustomobject]@{nodes=@($script:MockViews)}
      }
    }
    repository=[pscustomobject]@{id='REPO';nameWithOwner='rassvetpublic-spec/KAT9I_OS'}
  }
}

function Gql {
  param([string]$Query,[hashtable]$Variables)
  $script:GqlCalls++
  throw 'GraphQL mutation не должна выполняться в regression fail-closed сценарии.'
}

function Rest {
  param([string]$Endpoint,[string]$Method='GET',$Body=$null)
  if($Method -ne 'GET'){$script:RestWrites++}
  throw "REST не должен вызываться в regression fail-closed сценарии: $Method $Endpoint"
}

function gh {
  $global:LASTEXITCODE=0
  if($args.Count -ge 2 -and $args[0] -eq 'issue' -and $args[1] -eq 'list'){
    $global:LASTEXITCODE=$script:IssueListExitCode
    return '[{"url":"https://github.com/rassvetpublic-spec/KAT9I_OS/issues/101"}]'
  }
  if($args.Count -ge 2 -and $args[0] -eq 'pr' -and $args[1] -eq 'list'){
    $global:LASTEXITCODE=$script:PrListExitCode
    return '[]'
  }
  if($args.Count -ge 2 -and $args[0] -eq 'project' -and $args[1] -eq 'item-add'){
    $script:ItemAddCalls++
    $global:LASTEXITCODE=0
    return '{}'
  }
  throw "Неожиданный вызов gh: $($args -join ' ')"
}

function Assert-NoWrites([string]$Scenario){
  if($script:GqlCalls -ne 0){throw "${Scenario}: GraphQL calls = $($script:GqlCalls)"}
  if($script:RestWrites -ne 0){throw "${Scenario}: REST writes = $($script:RestWrites)"}
  if($script:ItemAddCalls -ne 0){throw "${Scenario}: item-add calls = $($script:ItemAddCalls)"}
}

function Assert-Throws([scriptblock]$Action,[string]$Expected,[string]$Scenario){
  $thrown=$false
  try { & $Action } catch {
    $thrown=$true
    if($_.Exception.Message -notmatch $Expected){
      throw "${Scenario}: получена другая ошибка: $($_.Exception.Message)"
    }
  }
  if(-not $thrown){throw "${Scenario}: ожидалась fail-closed ошибка."}
}

# 1a/1b. Ошибка полного списка Issues или PR должна остановить фактический production entrypoint до item-add.
$origEnsureLink=(Get-Command EnsureLink -CommandType Function).ScriptBlock
$origEnsureSelect=(Get-Command EnsureSelect -CommandType Function).ScriptBlock
$origEnsureIteration=(Get-Command EnsureIteration -CommandType Function).ScriptBlock
$origEnsureViews=(Get-Command EnsureViews -CommandType Function).ScriptBlock
try {
  Set-Item Function:\EnsureLink -Value {}
  Set-Item Function:\EnsureSelect -Value { param($Name,$Aliases,$Defs) }
  Set-Item Function:\EnsureIteration -Value {}
  Set-Item Function:\EnsureViews -Value {}

  Reset-State
  $script:IssueListExitCode=17
  Assert-Throws { Invoke-ProjectConfiguration $script:ProductionApply } 'Не удалось получить полный список открытых Issues' 'issue list failure'
  Assert-NoWrites 'issue list failure'

  Reset-State
  $script:PrListExitCode=23
  Assert-Throws { Invoke-ProjectConfiguration $script:ProductionApply } 'Не удалось получить полный список открытых PR' 'pr list failure'
  Assert-NoWrites 'pr list failure'
}
finally {
  Set-Item Function:\EnsureLink -Value $origEnsureLink
  Set-Item Function:\EnsureSelect -Value $origEnsureSelect
  Set-Item Function:\EnsureIteration -Value $origEnsureIteration
  Set-Item Function:\EnsureViews -Value $origEnsureViews
}

# 2. Один однозначный legacy alias должен блокировать небезопасную замену option ID.
Reset-State
$script:MockFields=@(
  New-StatusField @(
    [pscustomobject]@{id='O1';name='Todo'},
    [pscustomobject]@{id='O2';name='Нужно разобрать'},
    [pscustomobject]@{id='O3';name='Готово к работе'},
    [pscustomobject]@{id='O4';name='В работе'},
    [pscustomobject]@{id='O5';name='Проверка QA'},
    [pscustomobject]@{id='O6';name='Заблокировано'},
    [pscustomobject]@{id='O7';name='Готово'}
  )
)
Assert-Throws { Invoke-ProjectConfiguration $script:ProductionApply } 'требует изменения option ID' 'legacy option id migration'
Assert-NoWrites 'legacy option id migration'

# 3. Полностью посторонний View должен попасть в unknown/unexpected и остановить preflight до Apply.
Reset-State
$script:MockViews+=New-View '99 — Эксперимент' 'UNKNOWN' 'TABLE_LAYOUT' 'is:open'
Assert-Throws { Invoke-ProjectConfiguration $script:ProductionApply } 'неизвестные или регистрово отличающиеся представления' 'unknown view'
Assert-NoWrites 'unknown view'

Write-Host 'PASS: #101 regression — issue/pr list failures, legacy option ID migration и полностью неизвестный View fail-closed на реальном production entrypoint без mutation/write.'
