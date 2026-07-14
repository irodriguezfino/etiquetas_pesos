param(
  [Parameter(Mandatory=$true)][string]$Path
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not $env:WINDOWS_CODESIGN_CERTIFICATE_BASE64 -or -not $env:WINDOWS_CODESIGN_CERTIFICATE_PASSWORD) {
  Write-Host "Firma omitida: no hay certificado configurado. Define WINDOWS_CODESIGN_CERTIFICATE_BASE64 y WINDOWS_CODESIGN_CERTIFICATE_PASSWORD para produccion."
  exit 0
}

$certPath = Join-Path $env:TEMP "etiquetado_codesign.pfx"
[IO.File]::WriteAllBytes($certPath, [Convert]::FromBase64String($env:WINDOWS_CODESIGN_CERTIFICATE_BASE64))

$signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $signtool) { throw "No se encontro signtool.exe. Instala Windows SDK en el runner." }

Get-ChildItem -Path $Path -File -Recurse | Where-Object { $_.Extension -eq ".exe" } | ForEach-Object {
  & $signtool.Source sign /f $certPath /p $env:WINDOWS_CODESIGN_CERTIFICATE_PASSWORD /tr http://timestamp.digicert.com /td sha256 /fd sha256 $_.FullName
  & $signtool.Source verify /pa /v $_.FullName
}

Remove-Item -LiteralPath $certPath -Force
