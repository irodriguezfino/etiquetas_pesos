$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location (Split-Path -Parent $PSScriptRoot)
. .\scripts\_python.ps1

$runtime = Get-ProjectPython
$python = $runtime.Command
$pythonArgs = $runtime.Args
& $python @pythonArgs tools/versioning.py generate
if ($LASTEXITCODE -ne 0) { throw "No se pudieron generar los archivos de version." }
& $python @pythonArgs app_etiquetado_pesos.py
if ($LASTEXITCODE -ne 0) { throw "La aplicacion finalizo con error." }
