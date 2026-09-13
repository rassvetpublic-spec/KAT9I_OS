@echo off
setlocal
for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "CTRL=%ROOT%\_System\Antigravity-Control.ps1"
if not exist "%CTRL%" (
  echo [ERROR] Controller not found: "%CTRL%"
  exit /b 2
)
set "PS=powershell.exe"
where pwsh.exe >nul 2>nul
if not errorlevel 1 set "PS=pwsh.exe"
if "%~1"=="" goto :status
if /I "%~1"=="dryrun" goto :dryrun
"%PS%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%CTRL%" %* -Root "%ROOT%"
exit /b %errorlevel%

:status
"%PS%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%CTRL%" status -Root "%ROOT%"
exit /b %errorlevel%

:dryrun
echo [DRYRUN] Read-only compatibility/status check. No patch, fallback or state backup will be executed.
"%PS%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%CTRL%" status -Root "%ROOT%"
exit /b %errorlevel%
