@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo Este archivo se conserva por compatibilidad.
echo El flujo mantenido esta en scripts\prepare_release.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\prepare_release.ps1" -ReleaseNotes "Version preparada para GitHub Releases."
if errorlevel 1 (
    echo ERROR: No se pudo preparar la release.
    if /i "%~1" neq "--no-pause" pause
    exit /b 1
)
if /i "%~1" neq "--no-pause" pause
exit /b 0

for /f "delims=" %%V in ('python tools\versioning.py print-version') do set "APP_VERSION=%%V"
set "APP_TITLE=Etiquetado Pesos"
set "APP_LAUNCHER=Etiquetado_Pesos"
set "APP_MAIN=Etiquetado_Pesos_App"
set "APP_UPDATER=Etiquetado_Pesos_Updater"
set "APP_INSTALLER=Instalador_Etiquetado_Pesos_v%APP_VERSION%"
set "ICON_PATH=assets\ICONO_SUITE_RRHH.ico"
set "STAGING_DIR=dist\Etiquetado_Pesos_Instalado"
set "GITHUB_OWNER=irodriguezfino"
set "GITHUB_REPO=etiquetas_pesos"
set "GITHUB_DIR=github_release"
set "RELEASES_DIR=%GITHUB_DIR%\releases"
set "INSTALLERS_DIR=%GITHUB_DIR%\installers"
set "UPDATE_ZIP_NAME=Etiquetado_Pesos_v%APP_VERSION%_update.zip"
set "UPDATE_ZIP=%RELEASES_DIR%\%UPDATE_ZIP_NAME%"
set "INSTALLER_EXE=%INSTALLERS_DIR%\Instalador_Etiquetado_Pesos_v%APP_VERSION%.exe"

echo.
echo ============================================================
echo  CREAR INSTALADOR Y PAQUETE GITHUB - %APP_TITLE%
echo ============================================================
echo.

if not exist "%ICON_PATH%" (
    echo ERROR: No se encuentra el icono "%ICON_PATH%".
    pause
    exit /b 1
)

if not exist "config\config_salazon.csv" (
    echo ERROR: No se encuentra config\config_salazon.csv.
    pause
    exit /b 1
)

call :find_python
if not defined PY_CMD (
    echo ERROR: No se ha encontrado Python 3 en este equipo.
    pause
    exit /b 1
)

echo Python detectado:
%PY_CMD% --version
echo.

echo Comprobando dependencias de ejecucion...
%PY_CMD% -c "import PIL" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias de ejecucion desde requirements.txt...
    %PY_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: No se pudieron instalar las dependencias de ejecucion.
        pause
        exit /b 1
    )
) else (
    echo Dependencias de ejecucion OK.
)

echo.
echo Comprobando PyInstaller...
%PY_CMD% -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo Instalando PyInstaller...
    %PY_CMD% -m pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: No se pudo instalar PyInstaller.
        pause
        exit /b 1
    )
) else (
    echo PyInstaller OK.
)

echo.
echo Limpiando compilaciones anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "%RELEASES_DIR%" rmdir /s /q "%RELEASES_DIR%"
if exist "%INSTALLERS_DIR%" rmdir /s /q "%INSTALLERS_DIR%"
if exist "%GITHUB_DIR%\version.json" del /q "%GITHUB_DIR%\version.json"
if exist "%GITHUB_DIR%\README.md" del /q "%GITHUB_DIR%\README.md"
if exist "%APP_LAUNCHER%.spec" del /q "%APP_LAUNCHER%.spec"
if exist "%APP_MAIN%.spec" del /q "%APP_MAIN%.spec"
if exist "%APP_UPDATER%.spec" del /q "%APP_UPDATER%.spec"
if exist "%APP_INSTALLER%.spec" del /q "%APP_INSTALLER%.spec"
if not exist "%GITHUB_DIR%" mkdir "%GITHUB_DIR%"
mkdir "%RELEASES_DIR%"
mkdir "%INSTALLERS_DIR%"

echo.
echo Generando ejecutable principal...
%PY_CMD% -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --noconsole ^
    --onefile ^
    --name "%APP_MAIN%" ^
    --icon "%ICON_PATH%" ^
    --add-data "assets;assets" ^
    --add-data "config;config" ^
    --hidden-import win32print ^
    --hidden-import win32con ^
    --hidden-import win32ui ^
    --hidden-import PIL.ImageWin ^
    app_etiquetado_pesos.py
if errorlevel 1 (
    echo ERROR: PyInstaller no pudo generar %APP_MAIN%.exe.
    pause
    exit /b 1
)

echo.
echo Generando lanzador con actualizaciones automaticas...
%PY_CMD% -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --noconsole ^
    --onefile ^
    --name "%APP_LAUNCHER%" ^
    --icon "%ICON_PATH%" ^
    lanzador_pesos.py
if errorlevel 1 (
    echo ERROR: PyInstaller no pudo generar %APP_LAUNCHER%.exe.
    pause
    exit /b 1
)

echo.
echo Generando actualizador auxiliar...
%PY_CMD% -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --noconsole ^
    --onefile ^
    --name "%APP_UPDATER%" ^
    --icon "%ICON_PATH%" ^
    actualizador_pesos.py
if errorlevel 1 (
    echo ERROR: PyInstaller no pudo generar %APP_UPDATER%.exe.
    pause
    exit /b 1
)

echo.
echo Preparando carpeta instalada...
if exist "%STAGING_DIR%" rmdir /s /q "%STAGING_DIR%"
mkdir "%STAGING_DIR%"
copy /y "dist\%APP_LAUNCHER%.exe" "%STAGING_DIR%\%APP_LAUNCHER%.exe" >nul
copy /y "dist\%APP_MAIN%.exe" "%STAGING_DIR%\%APP_MAIN%.exe" >nul
copy /y "dist\%APP_UPDATER%.exe" "%STAGING_DIR%\%APP_UPDATER%.exe" >nul
copy /y "version_local.json" "%STAGING_DIR%\version_local.json" >nul
copy /y "update_config.json" "%STAGING_DIR%\update_config.json" >nul
copy /y "README.txt" "%STAGING_DIR%\README.txt" >nul
robocopy "assets" "%STAGING_DIR%\assets" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo ERROR: No se pudieron copiar assets.
    pause
    exit /b 1
)
robocopy "config" "%STAGING_DIR%\config" /E /XD "backups" /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo ERROR: No se pudo copiar config.
    pause
    exit /b 1
)

echo.
echo Creando ZIP de actualizacion...
if exist "%UPDATE_ZIP%" del /q "%UPDATE_ZIP%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%STAGING_DIR%\*' -DestinationPath '%UPDATE_ZIP%' -Force"
if errorlevel 1 (
    echo ERROR: No se pudo crear el ZIP de actualizacion.
    pause
    exit /b 1
)

for /f "tokens=* delims=" %%H in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-FileHash -Algorithm SHA256 '%UPDATE_ZIP%').Hash.ToLower()"') do set "UPDATE_SHA=%%H"
if not defined UPDATE_SHA (
    echo ERROR: No se pudo calcular el SHA256 del ZIP.
    pause
    exit /b 1
)

echo.
echo Generando version.json para GitHub...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$data=[ordered]@{version='%APP_VERSION%'; notes='Correccion de articulos con sufijo W para ocultar rangos en el selector.'; auto_update=[ordered]@{type='zip'; url='https://github.com/%GITHUB_OWNER%/%GITHUB_REPO%/raw/main/releases/%UPDATE_ZIP_NAME%'; file='%UPDATE_ZIP_NAME%'; sha256='%UPDATE_SHA%'}}; $data | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 '%GITHUB_DIR%\version.json'"
if errorlevel 1 (
    echo ERROR: No se pudo generar version.json.
    pause
    exit /b 1
)

echo.
echo Generando instalador unico autocontenido...
%PY_CMD% -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --noconsole ^
    --onefile ^
    --name "%APP_INSTALLER%" ^
    --icon "%ICON_PATH%" ^
    --add-data "%STAGING_DIR%;payload" ^
    instalador_pesos.py
if errorlevel 1 (
    echo ERROR: PyInstaller no pudo generar el instalador unico.
    pause
    exit /b 1
)

copy /y "dist\%APP_INSTALLER%.exe" "%INSTALLER_EXE%" >nul
if errorlevel 1 (
    echo ERROR: No se pudo copiar el instalador a github_release\installers.
    pause
    exit /b 1
)

echo.
echo Copiando README de repositorio GitHub...
if exist "README_GITHUB.md" copy /y "README_GITHUB.md" "%GITHUB_DIR%\README.md" >nul

echo.
echo ============================================================
echo  PAQUETE PREPARADO
echo ============================================================
echo.
echo Instalador unico:
echo "%INSTALLER_EXE%"
echo.
echo ZIP de actualizacion:
echo "%UPDATE_ZIP%"
echo.
echo Manifest:
echo "%GITHUB_DIR%\version.json"
echo.
echo Sube a GitHub SOLO el contenido de:
echo "%CD%\%GITHUB_DIR%"
echo.
if /i "%~1" neq "--no-pause" pause
exit /b 0

:find_python
set "PY_CMD="
if exist "%LocalAppData%\Python\pythoncore-3.14-64\python.exe" set "PY_CMD="%LocalAppData%\Python\pythoncore-3.14-64\python.exe""
if defined PY_CMD exit /b 0

if exist "%LocalAppData%\Python\bin\python.exe" set "PY_CMD="%LocalAppData%\Python\bin\python.exe""
if defined PY_CMD exit /b 0

for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PY_CMD set "PY_CMD="%%P""
)
if defined PY_CMD exit /b 0

where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
exit /b 0
