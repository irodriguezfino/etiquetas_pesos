function Get-ProjectPython {
  $candidates = @(
    @{ Command = "python"; Args = @() },
    @{ Command = "py"; Args = @("-3") },
    @{ Command = Join-Path $env:LocalAppData "Python\pythoncore-3.14-64\python.exe"; Args = @() },
    @{ Command = Join-Path $env:LocalAppData "Python\bin\python.exe"; Args = @() }
  )

  foreach ($candidate in $candidates) {
    $command = [string]$candidate.Command
    if ((Test-Path $command) -or (Get-Command $command -ErrorAction SilentlyContinue)) {
      return [PSCustomObject]@{ Command = $command; Args = [string[]]$candidate.Args }
    }
  }

  throw "No se encontro Python 3. Instala Python 3.10+ o anadelo a PATH."
}
