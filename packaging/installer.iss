; Inno Setup 6 script - makes a one-file installer: installer_output\DPet-Setup.exe
#define AppName "DPet"
#define AppVersion "1.0"

[Setup]
AppId={{6B1F6C0A-3C52-4B7E-9D63-0D9E7A11C001}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=..\installer_output
OutputBaseFilename=DPet-Setup
SetupIconFile=dpet.ico
UninstallDisplayIcon={app}\DPet.exe
Compression=lzma2
SolidCompression=yes
DisableProgramGroupPage=yes
WizardStyle=modern
CloseApplications=force

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Start DPet automatically when Windows starts"; GroupDescription: "Options:"

[Files]
Source: "..\dist\DPet\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\DPet.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\DPet.exe"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\DPet.exe"; Tasks: startup

[Run]
Filename: "{app}\DPet.exe"; Description: "Launch DPet now"; Flags: nowait postinstall skipifsilent
