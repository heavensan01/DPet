@echo off
title Build DPet desktop app
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

if not exist ".buildenv\Scripts\python.exe" (
  echo Creating build environment...
  %PY% -m venv .buildenv
)
echo Installing build tools (first time takes a few minutes)...
".buildenv\Scripts\python.exe" -m pip install --upgrade pip
".buildenv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto fail

echo.
echo Building DPet.exe ...
rmdir /s /q build dist >nul 2>&1
".buildenv\Scripts\python.exe" -m PyInstaller DPet.spec --noconfirm
if errorlevel 1 goto fail

echo.
echo === Desktop app ready:  dist\DPet\DPet.exe ===

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if defined ISCC (
  echo Building installer...
  "%ISCC%" packaging\installer.iss
  if errorlevel 1 goto fail
  echo === Installer ready:  installer_output\DPet-Setup.exe ===
) else (
  echo.
  echo Optional: install Inno Setup 6 from https://jrsoftware.org/isdl.php and run this file again
  echo to also get a one-file installer ^(DPet-Setup.exe^).
)
echo.
pause
exit /b 0

:notextracted
echo Please EXTRACT the zip first, then run this file again.
pause
exit /b 1

:nopython
echo Python 3.10+ is needed ONLY to build. Get it from https://www.python.org/downloads/
echo and TICK "Add Python to PATH" in its installer, then run this file again.
pause
exit /b 1

:fail
echo.
echo Something went wrong. Take a screenshot of this window and send it.
pause
exit /b 1
