@echo off
cd /d "%~dp0"
set "HERE=%~dp0"
set "TARGET=%HERE%2 START DPET.bat"
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DPET.lnk"
set "VBS=%TEMP%\dpet_shortcut.vbs"
> "%VBS%" echo Set s = CreateObject("WScript.Shell").CreateShortcut("%LNK%")
>> "%VBS%" echo s.TargetPath = "%TARGET%"
>> "%VBS%" echo s.WorkingDirectory = "%~dp0"
>> "%VBS%" echo s.WindowStyle = 7
>> "%VBS%" echo s.Save
cscript //nologo "%VBS%"
del "%VBS%"
echo.
echo DPET will now start automatically when Windows starts.
pause
