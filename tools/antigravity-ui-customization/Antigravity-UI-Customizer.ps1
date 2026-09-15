<#
.SYNOPSIS
    Утилита кастомизации интерфейса Antigravity Standalone (Electron).

.DESCRIPTION
    Внедряет контекстное меню по правой кнопке мыши с поддержкой буфера обмена,
    действий чата, вызова скилов и визуальной настройки прямо в UI.
    Поддерживает режимы:
      - status  : диагностика текущего состояния и резервной копии
      - install : создание бэкапа и внедрение кастомного UI в app.asar
      - restore : откат к оригинальному состоянию из резервной копии

.EXAMPLE
    .\Antigravity-UI-Customizer.ps1 -Command status
    .\Antigravity-UI-Customizer.ps1 -Command install
    .\Antigravity-UI-Customizer.ps1 -Command restore
#>

param(
    [Parameter(Position=0)]
    [ValidateSet('status','install','restore')]
    [string]$Command = 'status',

    [string]$CustomTarget = '',

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnginePath = Join-Path $ScriptDir 'patch-engine.js'

if (-not (Test-Path -LiteralPath $EnginePath)) {
    Write-Error "Не найден patch-engine.js в каталоге $ScriptDir"
    exit 1
}

# Проверка наличия Node.js
try {
    $nodeVer = & node -v 2>$null
    if (-not $nodeVer) {
        Write-Error "Node.js не обнаружен. Установите Node.js для работы утилиты кастомизации."
        exit 1
    }
} catch {
    Write-Error "Node.js не обнаружен в системе."
    exit 1
}

$nodeArgs = @($EnginePath, $Command)
if ($CustomTarget) {
    $nodeArgs += @('--target', $CustomTarget)
}

& node @nodeArgs
exit $LASTEXITCODE
