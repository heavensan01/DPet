@echo off
title DPET setup
cd /d "%~dp0"
if not exist "main.py" goto notextracted

set "PY="
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  python -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY goto nopython

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys" >nul 2>&1
  if errorlevel 1 (
    echo Removing a broken environment copied from another computer...
    rmdir /s /q ".venv"
  )
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating environment...
  %PY% -m venv .venv
)
if not exist ".venv\Scripts\python.exe" goto fail

echo.
echo Installing PySide6 (about 80 MB, please wait)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install --default-timeout=1000 --retries 10 -r requirements.txt
if errorlevel 1 goto fail

echo.
echo Setup finished!  Now double-click "2 START DPET.bat".
pause
exit /b 0

:notextracted
echo Please EXTRACT the zip first (right-click the zip, Extract All),
echo then open the extracted folder and run this file again.
pause
exit /b 1

:nopython
echo Python was not found on this computer.
echo 1. Download Python 3.10 or newer from https://www.python.org/downloads/
echo 2. In the installer, TICK "Add Python to PATH"
echo 3. Run this file again.
pause
exit /b 1

:fail
echo.
echo Something went wrong. Take a screenshot of this window and send it.
pause
exit /b 1
