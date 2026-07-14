@echo off
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 app_etiquetado_pesos.py
    exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
    python app_etiquetado_pesos.py
    exit /b %errorlevel%
)

echo No se encontro Python.
echo Instala Python 3 y las dependencias con: pip install -r requirements.txt
pause
exit /b 1
