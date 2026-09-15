param([string]$Path='project-preflight.json')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath $Path -PathType Leaf)){
  throw "PREFLIGHT_ARTIFACT_MISSING=$Path"
}
$json=Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
if($null -eq $json){throw "PREFLIGHT_ARTIFACT_INVALID=$Path"}
Write-Host "PREFLIGHT_ARTIFACT_OK=$Path"
