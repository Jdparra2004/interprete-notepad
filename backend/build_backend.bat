@echo off
REM =======================================================
REM build_backend.bat
REM Debes ejecutarlo desde:  Interpreter_Function\backend\
REM El venv debe existir en backend\venv
REM =======================================================

echo Activando entorno virtual...
call venv\Scripts\activate

if %errorlevel% neq 0 (
    echo NO se pudo activar el entorno virtual.
    echo Asegúrate de haber creado el venv dentro de backend\
    pause
    exit /b 1
)

echo Instalando dependencias necesarias...
pip install --upgrade pip
pip install flask requests

REM =======================================================
REM Limpiar builds previos
REM =======================================================
echo Limpiando carpetas build/ y dist/ previas...
if exist build rd /s /q build
if exist dist rd /s /q dist

REM =======================================================
REM Ejecutar PyInstaller
REM ===========================================
echo Compilando backend con PyInstaller...

pyinstaller --noconfirm --onefile ^
    --hidden-import=requests ^
    --hidden-import=core.pipeline ^
    --hidden-import=core.glossary ^
    --hidden-import=core.normalizer ^
    --hidden-import=core.protector ^
    --add-data "glossary.json;." ^
    --add-data "config.json;." ^
    --add-data "core;core" ^
    app.py

IF %ERRORLEVEL% NEQ 0 (
    echo =======================================================
    echo   ❌ PyInstaller FALLO - revisa el error de arriba
    echo =======================================================
    pause
    exit /b 1
)

echo =======================================================
echo   ✔ Backend compilado correctamente
echo   ✔ Archivo final: dist\app.exe
echo =======================================================
pause
