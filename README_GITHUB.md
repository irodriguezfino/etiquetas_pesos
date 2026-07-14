# Etiquetado Pesos - Releases

Repositorio para distribuir Etiquetado Pesos con GitHub Releases.

Archivos importantes:
- `pyproject.toml`: origen unico de version.
- `github_release/releases/update-manifest.json`: manifiesto generado para el actualizador.
- `github_release/releases/Etiquetado_Pesos_vX.Y.Z_update.zip`: paquete de actualizacion.
- `github_release/installers/Instalador_Etiquetado_Pesos_vX.Y.Z.exe`: instalador Windows.

Flujo de versiones:
1. Cambiar `project.version` en `pyproject.toml`.
2. Ejecutar `scripts\test.ps1`.
3. Crear una etiqueta `vX.Y.Z` que coincida con la version.
4. Subir la etiqueta para activar el workflow de publicacion.

El lanzador instalado consulta GitHub Releases, ignora prereleases salvo canal beta, valida SHA-256 y conserva datos de usuario.

Consulta `docs/RELEASE.md` antes de la primera publicacion.
