; inno_setup.iss - Byblos CRM v2 Installer
; Erstellt einen Setup-Installer aus dem PyInstaller-Build.
;
; VORAUSSETZUNG: build_exe.bat muss zuerst ausgefuehrt werden!
;   => dist\ByblosCRM\ByblosCRM.exe muss existieren.
;
; AUSFUEHREN (von Projektstamm oder installer\):
;   iscc installer\inno_setup.iss
;
; OUTPUT: installer\Output\ByblosCRMSetup_2.0.0.exe

#define MyAppName      "Byblos CRM"
#define MyAppVersion   "2.0.0"
#define MyAppPublisher "Byblos Sicherheitsdienst und Service"
#define MyAppExeName   "ByblosCRM.exe"
#define MyAppId        "{D4E7A2F1-8C3B-4A56-9E01-2B3C4D5E6F70}"

; Projektstamm: ein Verzeichnis ueber diesem Skript
#define ProjectRoot    ".."

[Setup]
AppId={{#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Output relativ zu diesem Skript
OutputDir={#ProjectRoot}\installer\Output
OutputBaseFilename=ByblosCRMSetup_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0.17763
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableDirPage=no
DisableProgramGroupPage=yes
CloseApplications=yes

[Languages]
Name: "german";  MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; PyInstaller-Build-Ordner relativ zum Projektstamm
Source: "{#ProjectRoot}\dist\ByblosCRM\*"; DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{#MyAppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
  WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill.exe"; Parameters: "/f /im {#MyAppExeName}"; \
  Flags: skipifdoesntexist runhidden
