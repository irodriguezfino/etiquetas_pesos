App Etiquetado Pesos
====================

Aplicacion Python para imprimir etiquetas de pesos usando el mismo sistema de plantilla grafica que Etiquetado Box.

Uso
---
1. Ejecutar ejecutar_etiquetado_pesos.bat.
2. Seleccionar un articulo de config/config_salazon.csv.
3. Seleccionar el rango de pesos disponible para ese articulo.
4. Introducir numero de albaran y numero de partida si se quieren mostrar en la etiqueta.
5. Generar vista previa y despues imprimir o guardar PNG.

Notas
-----
- La plantilla editable se guarda en config/plantilla_etiqueta_pesos.json.
- El editor grafico queda oculto como en Etiquetado Box: Ctrl+Alt+D y contrasena de administrador.
- La impresion exige generar primero la vista previa.
- Albaran y partida son opcionales y no bloquean la impresion.
- El articulo y el rango se seleccionan por separado para evitar etiquetas incorrectas.
- Para imprimir en Windows se usa pywin32. Si no esta disponible, se puede guardar PNG para pruebas.

Instalacion y actualizaciones
-----------------------------
- Ejecutar scripts\prepare_release.ps1 para generar ejecutables, ZIP de actualizacion, manifiesto, hashes e instalador.
- El acceso directo instalado abre Etiquetado_Pesos.exe, que abre la aplicacion y despues consulta GitHub Releases en segundo plano.
- Si hay version nueva estable, muestra notas, descarga el ZIP, valida el SHA-256 y aplica la actualizacion.
- La publicacion se realiza creando una etiqueta vX.Y.Z en GitHub; el workflow adjunta los artefactos a la Release.
