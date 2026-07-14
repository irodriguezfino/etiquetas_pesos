# Automatic Updates

## Flow

1. `Etiquetado_Pesos.exe` opens the real app immediately.
2. A few seconds later it queries GitHub Releases.
3. Stable channel uses the latest non-prerelease release.
4. Beta channel can use prereleases when enabled in `update_config.json`.
5. The updater shows the target version and release notes.
6. If the user accepts, the app window is closed before files are copied.
7. The ZIP is downloaded with progress and can be cancelled.
8. SHA-256 is verified before extraction.
9. Files are copied while preserving user configuration and exports.
10. The app is reopened after a successful update.

## Required release assets

- `Etiquetado_Pesos_vX.Y.Z_update.zip`
- `Etiquetado_Pesos_vX.Y.Z_update.zip.sha256`
- `update-manifest.json`
- Windows installer `.exe`

The updater can infer metadata from release assets, but `update-manifest.json` is uploaded for clarity and compatibility.

## Logs

Logs are written under:

```text
%LOCALAPPDATA%\Etiquetado Pesos\logs
```
