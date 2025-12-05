@echo off
REM -------------------------------------------------------
REM build_backend.bat
REM Ejecutar desde backend\ 
REM Asegúrate de activar venv antes de ejecutar este script
REM -------------------------------------------------------

REM 1) activar virtualenv (si se llamó venv)
call venv\Scripts\activate

REM 2) limpiar builds previos
if exist build rd /s /q build
if exist dist rd /s /q dist

REM 3) ejecutar pyinstaller
pyinstaller --noconfirm --onefile ^
    --add-data "glossary.json;." ^
    --add-data "config.json;." ^
    --add-data "core;core" ^
    app.py


IF %ERRORLEVEL% NEQ 0 (
    echo PyInstaller falló. Revisa el log.
    pause
    exit /b 1
)

echo Backend compilado. EXE en: dist\app.exe
pause
