@echo off
REM ============================================================
REM   BALANZIA INVEST - Lanzador rapido (el codigo ya esta aqui;
REM   este archivo vive junto a app.py). Doble clic para abrir.
REM ============================================================
setlocal
cd /d "%~dp0"
title Balanzia Invest - Copiloto de inversion

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

REM --- Crear acceso directo en el Escritorio (solo si no existe) ---
powershell -NoProfile -Command "$lnk=[Environment]::GetFolderPath('Desktop')+'\Balanzia Invest.lnk'; if(-not (Test-Path $lnk)){ $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($lnk); $s.TargetPath='%~f0'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%SystemRoot%\System32\shell32.dll,13'; $s.Description='Balanzia Invest'; $s.Save() }" 2>nul

echo.
echo Abriendo Balanzia Invest en http://localhost:8501  (cierra esta ventana para parar)
echo.
streamlit run app.py

pause
