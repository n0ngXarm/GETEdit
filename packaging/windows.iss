[Setup]
AppId=n0ngXarm.GETEdit
AppName=GETEdit
AppVersion=1.0.6
AppPublisher=n0ngXarm
AppPublisherURL=https://github.com/n0ngXarm/GETEdit
DefaultDirName={localappdata}\Programs\GETEdit
DefaultGroupName=GETEdit
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=GETEdit-1.0.6-windows-x64-setup
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\GETEdit.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
WizardStyle=modern
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "..\dist\GETEdit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\GETEdit"; Filename: "{app}\GETEdit.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\GETEdit"; Filename: "{app}\GETEdit.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\GETEdit.exe"; Description: "Open GETEdit"; Flags: nowait postinstall skipifsilent
