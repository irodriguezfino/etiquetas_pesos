$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Set-Location (Split-Path -Parent $PSScriptRoot)

$patterns = @(
  "AKIA[0-9A-Z]{16}",
  "gh[pousr]_[A-Za-z0-9_]{36,}",
  "github_pat_[A-Za-z0-9_]{80,}",
  "-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
  "(?i)(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*['""][^'""]{8,}['""]"
)

$excluded = "\\(.git|build|dist|__pycache__|github_release|.pytest_cache)\\"
$textExtensions = @(".bat", ".csv", ".ini", ".iss", ".json", ".md", ".ps1", ".py", ".toml", ".txt", ".yaml", ".yml")
$textNames = @(".gitattributes", ".gitignore", "LICENSE")
$files = Get-ChildItem -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object {
  $_.FullName -notmatch $excluded -and ($_.Extension -in $textExtensions -or $_.Name -in $textNames)
}
$findings = @()
foreach ($file in $files) {
  foreach ($pattern in $patterns) {
    $matches = Select-String -LiteralPath $file.FullName -Pattern $pattern -AllMatches -ErrorAction SilentlyContinue
    foreach ($match in $matches) {
      $findings += [PSCustomObject]@{ File = $file.FullName; Line = $match.LineNumber; Pattern = $pattern }
    }
  }
}

if ($findings.Count -gt 0) {
  $findings | Format-Table -AutoSize
  throw "La busqueda de secretos encontro posibles credenciales. Revisa antes de publicar."
}

Write-Host "No se detectaron secretos con los patrones configurados."
