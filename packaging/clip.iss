[Setup]
AppName=Clip
AppVersion=0.1.0
DefaultDirName={localappdata}\Programs\Clip
DefaultGroupName=Clip
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=Clip-Setup-0.1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Clip.exe

[Files]
Source: "..\dist\Clip\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Clip"; Filename: "{app}\Clip.exe"
Name: "{group}\User guide"; Filename: "{app}\USER_GUIDE.md"

[Run]
Filename: "{app}\Clip.exe"; Description: "Open Clip"; Flags: nowait postinstall skipifsilent
