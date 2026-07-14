#define MyAppName "Etiquetado Pesos"
#ifndef MyAppVersion
#define MyAppVersion "1.0.2"
#endif
#define MyAppPublisher "Rodriguez - Finura"
#define MyAppURL "https://github.com/irodriguezfino/etiquetas_pesos"
#define MyAppExeName "Etiquetado_Pesos.exe"
#define MyDistDir SourcePath + "\dist\Etiquetado_Pesos_Instalado"
#define MyOutputDir SourcePath + "\github_release\installers"

[Setup]
AppId={{6D97BB0E-CA57-4C7E-AB29-9F94104767D8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
AppVerName={#MyAppName} v{#MyAppVersion}
DefaultDirName={localappdata}\Programs\Etiquetado Pesos
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#MyOutputDir}
OutputBaseFilename=Instalador_Etiquetado_Pesos_v{#MyAppVersion}
SetupIconFile={#SourcePath}\assets\ICONO_SUITE_RRHH.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoProductName={#MyAppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Dirs]
Name: "{app}"
Name: "{app}\exportaciones"
Name: "{app}\config"

[Files]
Source: "{#MyDistDir}\*.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyDistDir}\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyDistDir}\version_local.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyDistDir}\update_config.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "{#MyDistDir}\README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyDistDir}\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
