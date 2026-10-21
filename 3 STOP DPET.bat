@echo off
cd /d "%~dp0"
if not exist dpet.pid goto none
set /p PID=<dpet.pid
taskkill /PID %PID% /F >nul 2>&1
del dpet.pid >nul 2>&1
echo DPET stopped.
goto end
:none
echo DPET is not running.
:end
timeout /t 2 >nul
