param(
  [string]$ReleaseNotes = "Version preparada para GitHub Releases."
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location (Split-Path -Parent $PSScriptRoot)
. .\scripts\_python.ps1

$runtime = Get-ProjectPython
$python = $runtime.Command
$pythonArgs = $runtime.Args
$icon = "assets\ICONO_SUITE_RRHH.ico"
$staging = "dist\Etiquetado_Pesos_Instalado"

& $python @pythonArgs tools/versioning.py generate
$version = (& $python @pythonArgs tools/versioning.py print-version).Trim()

if (-not (Test-Path $icon)) { throw "No se encuentra el icono $icon." }
if (-not (Test-Path "config\config_salazon.csv")) { throw "No se encuentra config\config_salazon.csv." }

New-Item -ItemType Directory -Force -Path "github_release\releases", "github_release\installers" | Out-Null

& $python @pythonArgs -m PyInstaller --noconfirm --clean --noconsole --onefile --name "Etiquetado_Pesos_App" --icon $icon --version-file "build\version_info.txt" --add-data "assets;assets" --add-data "config;config" --hidden-import win32print --hidden-import win32con --hidden-import win32ui --hidden-import PIL.ImageWin app_etiquetado_pesos.py
& $python @pythonArgs -m PyInstaller --noconfirm --clean --noconsole --onefile --name "Etiquetado_Pesos" --icon $icon --version-file "build\version_info.txt" lanzador_pesos.py
& $python @pythonArgs -m PyInstaller --noconfirm --clean --noconsole --onefile --name "Etiquetado_Pesos_Updater" --icon $icon --version-file "build\version_info.txt" actualizador_pesos.py

if (Test-Path $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path $staging | Out-Null
Copy-Item "dist\Etiquetado_Pesos.exe" $staging
Copy-Item "dist\Etiquetado_Pesos_App.exe" $staging
Copy-Item "dist\Etiquetado_Pesos_Updater.exe" $staging
Copy-Item "version_local.json" $staging
Copy-Item "update_config.json" $staging
Copy-Item "README.txt" $staging
Copy-Item "assets" "$staging\assets" -Recurse
New-Item -ItemType Directory -Force -Path "$staging\config" | Out-Null
Copy-Item "config\articulos.txt" "$staging\config" -ErrorAction SilentlyContinue
Copy-Item "config\config_salazon.csv" "$staging\config"
Copy-Item "config\plantilla_etiqueta_pesos.json" "$staging\config"

$zipName = "Etiquetado_Pesos_v${version}_update.zip"
$zipPath = "github_release\releases\$zipName"
if (Test-Path $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
Compress-Archive -Path "$staging\*" -DestinationPath $zipPath -Force
& $python @pythonArgs tools/versioning.py manifest --zip $zipPath --out "github_release\releases" --notes $ReleaseNotes

Write-Host "Build preparado: $zipPath"
