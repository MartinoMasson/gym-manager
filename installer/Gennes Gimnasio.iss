; installer/gym-manager.iss
;
; Genera el instalador de GymManager con Inno Setup.
; Requiere: https://jrsoftware.org/isinfo.php (gratis)
;
; Compilar desde linea de comandos:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\gym-manager.iss
;
; El instalador resultante queda en installer\output\GymManager-Setup-<version>.exe

#define MyAppName "Gennes Gimnasio"
#define MyAppVersion "1.0.1"
#define MyAppExeName "Gennes Gimnasio.exe"
#define BuildDir "..\dist\Gennes Gimnasio"

[Setup]
AppId={{B6C1E1B2-6E6B-4B1E-9B36-GYMMANAGER01}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Requiere administrador: instala en Program Files, para todas las PCs
PrivilegesRequired=admin
OutputDir=output
OutputBaseFilename=GymManager-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
; No pedir reinicio ni mostrar pantallas de mas: bueno para updates silenciosos
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
; Copia TODO el contenido de dist/gym-manager (exe, dlls, migrations/,
; alembic.ini, assets/, .env.template, gymmanager_template.db) a la
; carpeta de instalacion. recursesubdirs asegura que entren subcarpetas.
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"

[Run]
; Al terminar de instalar (o actualizar), lanzar la app.
; /SP- evita la pregunta inicial "Esto va a instalar..."; /VERYSILENT y
; /SUPPRESSMSGBOXES los usa el updater para que no aparezca ninguna
; ventana durante una actualizacion automatica.
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName}"; Flags: nowait postinstall skipifsilent

; NOTA IMPORTANTE:
; Este instalador NO toca %ProgramData%\GymManager (donde viven
; .env y gymmanager.db reales). Esa carpeta la crea y llena la propia
; app la primera vez que corre, copiando los templates empaquetados
; (ver asegurar_archivos_iniciales() en app/utils/paths.py). Por eso
; instalar/actualizar nunca borra los datos del gimnasio.
