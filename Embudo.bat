@echo off
REM ============================================================
REM   EMBUDO - Lanzador rapido (usar cuando el codigo ya esta
REM   descargado; este archivo vive junto a app.py).
REM   Doble clic para abrir la app.
REM ============================================================
setlocal
cd /d "%~dp0"
title Embudo - Copiloto de inversion

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python no esta en el PATH. Instalalo desde
  echo https://www.python.org/downloads/windows/  (marca "Add python.exe to PATH")
  pause
  exit /b 1
)

if not exist ".venv\" (
  echo Creando entorno virtual...
  python -m venv .venv
)

call .venv\Scripts\activate.bat
echo Comprobando dependencias...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

echo.
echo Abriendo Embudo en http://localhost:8501  (cierra esta ventana para parar)
echo.
streamlit run app.py

pause
