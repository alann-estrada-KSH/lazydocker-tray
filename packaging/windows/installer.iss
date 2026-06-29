; Inno Setup script for lazydocker-tray.
; Version is passed on the command line: iscc /DMyAppVersion=x.x.x installer.iss
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppName "LazyDocker Tray"
#define MyAppExe "lazydocker-tray.exe"

[Setup]
AppId={{A7E3F1C2-9B4D-4E8A-8C12-LAZYDOCKERTRAY}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Alan Estrada
DefaultDirName={autopf}\LazyDockerTray
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=LazyDockerTray-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
WizardStyle=modern

[Tasks]
Name: "startupicon"; Description: "Iniciar al arrancar Windows"; GroupDescription: "Inicio:"

[Files]
; The PyInstaller onefile exe is expected next to this script (copied by CI).
Source: "{#MyAppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Iniciar {#MyAppName}"; Flags: nowait postinstall skipifsilent
