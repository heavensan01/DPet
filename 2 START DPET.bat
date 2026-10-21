@echo off
cd /d "%~dp0"
if not exist "main.py" goto notextracted
if not exist ".venv\Scripts\pythonw.exe" goto nosetup
".venv\Scripts\python.exe" -c "import PySide6" >nul 2>&1
if errorlevel 1 goto nosetup
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0

:notextracted
echo Please EXTRACT the zip first (right-click the zip, Extract All).
pause
exit /b 1

:nosetup
echo DPET is not set up on this computer yet.
echo Please run "1 SETUP (first time only).bat" first, then start again.
pause
exit /b 1
