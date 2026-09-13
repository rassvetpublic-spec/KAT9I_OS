@echo off
setlocal
set "ROOT=%~dp0"
set "CTRL=%ROOT%_System\Antigravity-Control.ps1"
if not exist "%CTRL%" (
  echo [ERROR] Controller not found: "%CTRL%"
  exit /b 2
)
set "PS=powershell.exe"
where pwsh.exe >nul 2>nul
if not errorlevel 1 set "PS=pwsh.exe"
if "%~1"=="" (
  "%PS%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%CTRL%" status
  exit /b %errorlevel%
)
"%PS%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%CTRL%" %*
exit /b %errorlevel%
