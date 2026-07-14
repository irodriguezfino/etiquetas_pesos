# Build and Installer

## Clean build

```powershell
./scripts/install_deps.ps1
./scripts/prepare_release.ps1 -ReleaseNotes "Release notes"
```

## Individual steps

```powershell
./scripts/clean.ps1
./scripts/build.ps1 -ReleaseNotes "Release notes"
./scripts/installer.ps1
./scripts/hash.ps1 -Path github_release
```

## Requirements

- Windows
- Python 3.10+
- Inno Setup 6 for the installer
- Optional Windows SDK for `signtool.exe`

The installer uses per-user installation under `%LOCALAPPDATA%\Programs\Etiquetado Pesos` and does not require administrator privileges.
