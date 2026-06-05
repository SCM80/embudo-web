@echo off
REM ============================================================
REM   EMBUDO - Instalador y lanzador todo-en-uno para Windows
REM   Guarda este archivo en:  Escritorio\bolsa
REM   y haz DOBLE CLIC. La primera vez descarga e instala todo;
REM   las siguientes solo abre la app.
REM ============================================================
setlocal
cd /d "%~dp0"
title Embudo - Copiloto de inversion

set REPO=https://github.com/SCM80/embudo-web.git
set BRANCH=claude/stock-analysis-investment-tool-rvG42
set FOLDER=embudo-web

echo.
echo ===== EMBUDO =====
echo.

REM --- 1) Comprobar Git ---
where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Git no esta instalado.
  echo Instalalo desde: https://git-scm.com/download/win
  echo Luego vuelve a hacer doble clic en este archivo.
  pause
  exit /b 1
)

REM --- 2) Comprobar Python ---
where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python no esta instalado o no esta en el PATH.
  echo Instalalo desde: https://www.python.org/downloads/windows/
  echo IMPORTANTE: marca la casilla "Add python.exe to PATH" al instalar.
  pause
  exit /b 1
)

REM --- 3) Descargar el codigo (solo la primera vez) ---
if not exist "%FOLDER%\" (
  echo Descargando Embudo por primera vez...
  git clone --branch %BRANCH% %REPO% %FOLDER%
  if errorlevel 1 (
    echo [ERROR] No se pudo descargar el repositorio.
    echo Si te pide iniciar sesion en GitHub, hazlo en el navegador que se abra.
    pause
    exit /b 1
  )
) else (
  echo Actualizando Embudo a la ultima version...
  cd "%FOLDER%"
  git pull origin %BRANCH%
  cd ..
)

cd "%FOLDER%"

REM --- 4) Entorno virtual (solo la primera vez) ---
if not exist ".venv\" (
  echo Creando entorno virtual...
  python -m venv .venv
)

REM --- 5) Activar e instalar dependencias ---
call .venv\Scripts\activate.bat
echo Instalando dependencias (la primera vez tarda un par de minutos)...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

REM --- 6) Lanzar la app ---
echo.
echo Abriendo Embudo en tu navegador (http://localhost:8501) ...
echo Para cerrar la app: cierra esta ventana negra.
echo.
streamlit run app.py

pause
