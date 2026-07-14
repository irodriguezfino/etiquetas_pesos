$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location (Split-Path -Parent $PSScriptRoot)
. .\scripts\_python.ps1

$runtime = Get-ProjectPython
$python = $runtime.Command
$pythonArgs = $runtime.Args
& $python @pythonArgs tools/versioning.py generate
& $python @pythonArgs app_etiquetado_pesos.py
