@echo off
REM ============================================================================
REM Script: start_veda.cmd
REM Purpose: Launch Veda AI application or trigger automated bootstrap sequence
REM Author: Veda AI Team
REM Date: 2026-09-12
REM ============================================================================
setlocal EnableExtensions EnableDelayedExpansion

title Veda AI - Launcher
cd /d "%~dp0"

color 0B

echo ==========================================================================
echo   __     _______ ____    _       _    ___ 
echo   \ \   / / ____^|  _ \  / \     / \  ^|_ _^|
echo    \ \ / /^|  _^|  ^| ^| ^| / _ \   / _ \  ^| ^| 
echo     \ V / ^| ^|___ ^| ^|_^|/ ___ \ / ___ \ ^| ^| 
echo      \_/  ^|_____^|____/_/   \_/_/   \_\___^|
echo.
echo                       VEDA AI
echo ==========================================================================
echo.
if exist "%~dp0.venv\Scripts\python.exe" (
  echo Starting Veda AI...
  start "" "%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
  exit /b 0
)

echo Launching automated bootstrap sequence...

powershell.exe -ExecutionPolicy RemoteSigned -File "%~dp0bootstrap.ps1"

if %errorlevel% neq 0 (
  echo ERROR: Bootstrap failed.
  pause
  exit /b %errorlevel%
)
exit /b 0
