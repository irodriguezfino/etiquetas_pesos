$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location (Split-Path -Parent $PSScriptRoot)
. .\scripts\_python.ps1

$runtime = Get-ProjectPython
$python = $runtime.Command
$pythonArgs = $runtime.Args
$version = (& $python @pythonArgs tools/versioning.py print-version).Trim()
if ($LASTEXITCODE -ne 0) { throw "No se pudo leer la version del proyecto." }
$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
  $default = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
  if (Test-Path $default) { $iscc = Get-Item $default }
}
if (-not $iscc) { throw "No se encontro Inno Setup 6 (ISCC.exe). Instala Inno Setup para crear el instalador." }
if (-not (Test-Path "dist\Etiquetado_Pesos_Instalado\Etiquetado_Pesos.exe")) { throw "Ejecuta scripts\build.ps1 antes de crear el instalador." }

& $iscc.Source "/DMyAppVersion=$version" "instalador_etiquetado_pesos.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup no pudo crear el instalador." }
