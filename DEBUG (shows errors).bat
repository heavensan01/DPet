@echo off
title DPET debug
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run "1 SETUP (first time only).bat" first.
  pause
  exit /b 1
)
echo Starting DPET with a visible console. Close this window or use Quit to stop it.
".venv\Scripts\python.exe" main.py
echo.
echo DPET stopped. If you see an error above, take a screenshot and send it.
if exist dpet.log (
  echo ---- dpet.log ----
  type dpet.log
)
pause
