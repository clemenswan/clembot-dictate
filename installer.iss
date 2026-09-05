; Clembot-dictate Installer
; Built with Inno Setup 6 — https://jrsoftware.org/isinfo.php
;
; No admin rights required — installs to %LOCALAPPDATA%\Programs\Clembot-dictate
; Compile: ISCC.exe installer.iss  (or run build.bat — it calls ISCC automatically)

#define AppName "Clembot-dictate"
#define AppVersion "1.3.0"
#define AppPublisher "Wanessa Labs"
#define AppURL "https://wanessalabs.com"
#define AppExeName "Clembot-dictate.exe"

[Setup]
AppId={{E4A1C3F7-8B2D-4E9A-A6C0-1D3F5B7E9A2C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableDirPage=yes
DisableProgramGroupPage=yes
; No admin required — %LOCALAPPDATA% is always writable by the current user
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
; Kill any running instance before overwriting files on upgrade
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Entire PyInstaller output folder — recurse so all DLLs and data files are included
Source: "dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataPath: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Remove HKCU startup registry entry if the user had it enabled
    RegDeleteValue(
      HKEY_CURRENT_USER,
      'Software\Microsoft\Windows\CurrentVersion\Run',
      'Clembot-dictate'
    );

    // Offer to remove history, logs, and settings from AppData
    AppDataPath := ExpandConstant('{userappdata}\Clembot-dictate');
    if DirExists(AppDataPath) then
    begin
      if MsgBox(
        'Remove your history, logs, and settings?' + #13#10 + #13#10 + AppDataPath,
        mbConfirmation,
        MB_YESNO
      ) = IDYES then
        DelTree(AppDataPath, True, True, True);
    end;
  end;
end;
