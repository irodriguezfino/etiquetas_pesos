param(
  [string]$Path = "github_release"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location (Split-Path -Parent $PSScriptRoot)

Get-ChildItem -Path $Path -File -Recurse | Where-Object { $_.Extension -in ".exe", ".zip", ".json" } | ForEach-Object {
  $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName
  [PSCustomObject]@{ SHA256 = $hash.Hash.ToLower(); File = $_.FullName }
}
