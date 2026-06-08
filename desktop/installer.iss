[Setup]
AppName=ActifyXAI
AppVersion=1.0
DefaultDirName={autopf}\ActifyXAI
DefaultGroupName=ActifyXAI
OutputDir=.\installer
OutputBaseFilename=ActifyXAI_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\ActifyXAI.exe

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startup"; Description: "Start ActifyXAI on system startup"; GroupDescription: "Startup:"

[Files]
; The compiled executable
Source: "dist\ActifyXAI.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\ActifyXAI"; Filename: "{app}\ActifyXAI.exe"
Name: "{group}\Uninstall ActifyXAI"; Filename: "{uninstallexe}"
; Desktop
Name: "{autodesktop}\ActifyXAI"; Filename: "{app}\ActifyXAI.exe"; Tasks: desktopicon
; Startup
Name: "{userstartup}\ActifyXAI"; Filename: "{app}\ActifyXAI.exe"; Tasks: startup

[Run]
Filename: "{app}\ActifyXAI.exe"; Description: "Launch ActifyXAI"; Flags: nowait postinstall skipifsilent

[Code]
// If you want to perform cleanup or registry edits during installation, place PascalScript code here.
