# Etiquetado Pesos

Aplicacion Windows en Python/Tkinter para generar e imprimir etiquetas de pesos. El proyecto queda preparado para distribuirse con ejecutables PyInstaller, instalador Inno Setup y actualizaciones automaticas desde GitHub Releases.

## Tecnologia

- Python 3.10+
- Tkinter para interfaz grafica
- Pillow para imagenes
- pywin32 para impresion en Windows
- PyInstaller para ejecutables
- Inno Setup para instalador Windows

## Desarrollo

```powershell
./scripts/install_deps.ps1
./scripts/dev.ps1
```

## Pruebas

```powershell
./scripts/test.ps1
```

## Build local

```powershell
./scripts/prepare_release.ps1 -ReleaseNotes "Primera version publica"
```

El resultado se genera en `github_release/`:

- `releases/Etiquetado_Pesos_vX.Y.Z_update.zip`
- `releases/update-manifest.json`
- `releases/*.sha256`
- `installers/Instalador_Etiquetado_Pesos_vX.Y.Z.exe`

## Version

La version unica se declara en `pyproject.toml` (`project.version`). Los archivos derivados, como `version_local.json` y `build/version_info.txt`, se generan con:

```powershell
python tools/versioning.py generate
```

## Actualizaciones

La aplicacion consulta GitHub Releases sin bloquear la apertura. El canal estable ignora prereleases. Para beta, configurar `update_config.json` con `"enable_beta": true` o `"channel": "beta"`.

Ver [docs/UPDATES.md](docs/UPDATES.md).

## Publicacion

Las releases se publican creando una etiqueta `vX.Y.Z` que coincida con `pyproject.toml`.

```powershell
git tag -a v1.0.3 -m "Release v1.0.3"
git push origin v1.0.3
```

Ver [docs/RELEASE.md](docs/RELEASE.md).
