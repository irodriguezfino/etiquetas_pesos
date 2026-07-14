param(
  [string]$ReleaseNotes = "Version preparada para GitHub Releases."
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location (Split-Path -Parent $PSScriptRoot)

& .\scripts\clean.ps1
& .\scripts\build.ps1 -ReleaseNotes $ReleaseNotes
& .\scripts\installer.ps1
& .\scripts\hash.ps1 -Path "github_release"
