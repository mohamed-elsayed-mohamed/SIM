; Inno Setup 6 — x64 installer for SIM pipeline outputs (DLL drop + optional Unity player).
; Used by Docker build (docker-build.ps1). Manual: ISCC.exe SIM-Setup.iss /DMyAppVersion=... /DStagingDir=... /DInnoOutputDir=...
;
; Staging + output: build.py and Docker pass the same absolute paths:
;   /DStagingDir=<publish folder>  /DInnoOutputDir=<publish folder>
; so SIM-Setup-x64-*.exe is written next to DLLs and manifest (no separate InnoStaging folder).
;
; Command line (optional defines):
;   ISCC.exe SIM-Setup.iss /DMyAppVersion=1.0.0 /DStagingDir=C:/path/to/drop /DInnoOutputDir=C:/path/to/drop /DIncludeUnity

#define MyAppName "SIM Case Study"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
; Staging dir is relative to this .iss file (Build\InnoSetup\)
#ifndef StagingDir
  #define StagingDir "..\..\artifacts\InnoStaging"
#endif
; Where SIM-Setup-x64-*.exe is written (default: repo artifacts\; Docker passes /DInnoOutputDir=... )
#ifndef InnoOutputDir
  #define InnoOutputDir "..\..\artifacts"
#endif

[Setup]
AppId={{B4E8F1A2-9C3D-4E5F-8A7B-6D5C4E3F2A10}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=SIM
DefaultDirName={autopf64}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir={#InnoOutputDir}
OutputBaseFilename=SIM-Setup-x64-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
; 64-bit Windows only (see Inno "Architecture Identifiers" — x64 was deprecated in 6.4+)
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
DisableProgramGroupPage=no
UninstallDisplayIcon={uninstallexe}
; 64-bit Windows only
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#StagingDir}\ProjectA.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StagingDir}\ProjectB.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StagingDir}\ProjectC.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StagingDir}\ProjectD_net8.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StagingDir}\ProjectD_netstandard2.1.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StagingDir}\manifest.json"; DestDir: "{app}"; Flags: ignoreversion
#ifdef IncludeUnity
Source: "{#StagingDir}\ProjectE-StandaloneWindows64\*"; DestDir: "{app}\ProjectE"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Icons]
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{group}\SIM artifacts"; Filename: "{win}\explorer.exe"; Parameters: """{app}"""; IconFilename: "{win}\explorer.exe"
#ifdef IncludeUnity
Name: "{group}\SIM ProjectE"; Filename: "{app}\ProjectE\ProjectE.exe"; WorkingDir: "{app}\ProjectE"
Name: "{commondesktop}\SIM ProjectE"; Filename: "{app}\ProjectE\ProjectE.exe"; Tasks: desktopicon; WorkingDir: "{app}\ProjectE"
#endif

[Run]
Filename: "{win}\explorer.exe"; Parameters: """{app}"""; Description: "Open install folder"; Flags: postinstall skipifsilent unchecked
