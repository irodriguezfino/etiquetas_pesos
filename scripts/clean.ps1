$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location (Split-Path -Parent $PSScriptRoot)

$paths = @("build", "dist", "github_release")
foreach ($path in $paths) {
  $resolved = Resolve-Path $path -ErrorAction SilentlyContinue
  if ($resolved) {
    Remove-Item -LiteralPath $resolved.Path -Recurse -Force
  }
}

Get-ChildItem -Path . -Filter "*.spec" -File | Where-Object { $_.Name -like "Etiquetado_Pesos*.spec" } | Remove-Item -Force
New-Item -ItemType Directory -Force -Path "github_release\releases", "github_release\installers" | Out-Null
