@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Veda AI - Launcher
cd /d "%~dp0"

color 0B

echo ==========================================================================
echo   __     _______ ____    _       _    ___ 
echo   \ \   / / ____|  _ \  / \     / \  |_ _|
echo    \ \ / /|  _|  | | | / _ \   / _ \  | | 
echo     \ V / | |___ | |_|/ ___ \ / ___ \ | | 
echo      \_/  |_____|____/_/   \_/_/   \_\___|
echo.
echo                       VEDA AI
echo ==========================================================================
echo.
echo Launching automated bootstrap sequence...

powershell.exe -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1"

if %errorlevel% neq 0 (
  echo ERROR: Bootstrap failed.
  pause
  exit /b %errorlevel%
)
exit /b 0
