; ============================================================
; Byblos CRM v2 - Inno Setup Script (REPARIERT)
; Behebt: DeleteFile Code 5 - Zugriff verweigert
; Behebt: PyInstaller multiprocessing PermissionError
; ============================================================

#define AppName "Byblos CRM"
#define AppVersion "2.0"
#define AppPublisher "Byblos Sicherheitsdienst"
#define AppURL "https://byblos.de"
#define AppExeName "ByblosCRM.exe"

[Setup]
AppId={{B8F9C2A1-4E7D-4F3A-9B8C-1D2E3F4A5B6C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
LicenseFile=
OutputDir=dist_inno
OutputBaseFilename=ByblosCRM_v2_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; WICHTIG: Beendet laufende App vor Installation
CloseApplications=yes
CloseApplicationsFilter=*ByblosCRM*,*streamlit*
RestartApplications=no
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Kein Admin erforderlich - installiert für aktuellen User
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startmenuicon"; Description: "Startmenü-Eintrag erstellen"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked

[Files]
; Hauptprogramm (KEIN PyInstaller EXE - direkt Python nutzen)
Source: "launch_byblos.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "byblos_crm_app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "install_deps.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\launch_byblos.bat"; WorkingDir: "{app}\app"; Comment: "Byblos CRM v2 starten"; Tasks: startmenuicon
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\launch_byblos.bat"; WorkingDir: "{app}\app"; Comment: "Byblos CRM v2 starten"; Tasks: desktopicon

[Run]
; Abhängigkeiten installieren nach Setup
Filename: "{app}\install_deps.bat"; Description: "Python-Pakete installieren"; Flags: runhidden waituntilterminated
; App direkt starten
Filename: "{app}\launch_byblos.bat"; Description: "Byblos CRM jetzt starten"; Flags: postinstall nowait skipifsilent

[UninstallRun]
; App vor Deinstallation beenden
Filename: "cmd.exe"; Parameters: "/C taskkill /F /IM python.exe /IM pythonw.exe /IM streamlit.exe 2>nul"; Flags: runhidden

[Code]
// Prüft ob Python installiert ist
function IsPythonInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/C python --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
  if not Result then
    Result := Exec('cmd.exe', '/C py --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

// Beendet laufende Prozesse VOR Installation
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then begin
    // Alle relevanten Prozesse zwangsweise beenden
    Exec('cmd.exe', '/C taskkill /F /IM ByblosCRM.exe /IM python.exe /IM pythonw.exe /IM streamlit.exe 2>nul', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('cmd.exe', '/C timeout /t 2 /nobreak >nul', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

// Warnung wenn Python fehlt
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not IsPythonInstalled() then begin
    MsgBox('Python ist nicht installiert!' + #13#10 + #13#10 +
           'Bitte installieren Sie zuerst Python 3.11:' + #13#10 +
           'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' + #13#10 + #13#10 +
           'WICHTIG: "Add Python to PATH" anwaehlen!' + #13#10 + #13#10 +
           'Der Installer wird trotzdem fortfahren - Python wird später benötigt.',
           mbInformation, MB_OK);
  end;
end;
