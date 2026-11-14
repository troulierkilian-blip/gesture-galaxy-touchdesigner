@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\launch.ps1"
if errorlevel 1 (
  echo.
  echo Startup failed. See README.md for dependency and TouchDesigner setup.
  pause
  exit /b 1
)
