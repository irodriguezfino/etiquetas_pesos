# Etiquetado Pesos - Actualizaciones

Repositorio minimo para distribuir Etiquetado Pesos.

Archivos importantes:
- `version.json`: manifiesto que consulta el lanzador al abrir la aplicacion.
- `releases/Etiquetado_Pesos_vX.Y.Z_update.zip`: paquete rapido de actualizacion automatica.
- `installers/Instalador_Etiquetado_Pesos_vX.Y.Z.exe`: instalador unico para equipos nuevos.

Flujo de versiones:
1. Cambiar `APP_VERSION` en `crear_instalador_completo.bat`.
2. Cambiar `version_local.json` a la misma version.
3. Ejecutar `crear_instalador_completo.bat`.
4. Subir a este repositorio solo el contenido de `github_release`.

El lanzador instalado lee `version.json`, compara la version local y, si hay una version nueva, descarga el ZIP indicado, valida su SHA-256 y aplica la actualizacion.
