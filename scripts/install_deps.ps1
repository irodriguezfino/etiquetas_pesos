$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location (Split-Path -Parent $PSScriptRoot)
. .\scripts\_python.ps1

$runtime = Get-ProjectPython
$python = $runtime.Command
$pythonArgs = $runtime.Args
& $python @pythonArgs -m pip install --upgrade pip
& $python @pythonArgs -m pip install -r requirements.txt
& $python @pythonArgs -m pip install "pyinstaller>=6.0" "pytest>=8.0"
