$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location (Split-Path -Parent $PSScriptRoot)
. .\scripts\_python.ps1

$runtime = Get-ProjectPython
$python = $runtime.Command
$pythonArgs = $runtime.Args
& $python @pythonArgs tools/versioning.py generate
& $python @pythonArgs -m compileall -q app_etiquetado_pesos.py lanzador_pesos.py actualizador_pesos.py instalador_pesos.py logica_etiquetas.py editor_etiquetas.py estilos_suite.py tools
& $python @pythonArgs -m pytest -q
