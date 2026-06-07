# 🪟 Ejecutar Balanzia Invest en Windows (local)

Balanzia Invest es una app web en Python (Streamlit). No es un `.exe` clásico, pero con
el lanzador `.bat` funciona como si lo fuera: **doble clic y se abre en tu
navegador**.

## Opción fácil: instalador todo-en-uno

1. Crea una carpeta en el Escritorio llamada **`bolsa`**.
2. Copia dentro el archivo **`Instalar-BalanziaInvest.bat`**.
3. **Haz doble clic** en `Instalar-BalanziaInvest.bat`.
   - La primera vez: descarga el código, crea el entorno e instala todo
     (tarda un par de minutos). Si te pide iniciar sesión en GitHub, hazlo en
     el navegador que se abra.
   - Las siguientes veces: solo actualiza y abre la app.
4. Se abrirá Balanzia Invest en `http://localhost:8501`.
5. Para cerrarlo: cierra la ventana negra (consola).

### Requisitos (se instalan una sola vez)
- **Git para Windows**: https://git-scm.com/download/win
- **Python 3.11+**: https://www.python.org/downloads/windows/
  ⚠️ Marca **"Add python.exe to PATH"** durante la instalación.

Si falta alguno, el `.bat` te avisa con el enlace de descarga.

## Opción manual (si ya clonaste el repo)

Si ya tienes la carpeta del proyecto, usa **`BalanziaInvest.bat`** (está junto a
`app.py`): doble clic y listo.

O por línea de comandos (PowerShell) dentro de la carpeta del proyecto:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## (Opcional) Crear un acceso directo en el Escritorio
Clic derecho sobre `Instalar-BalanziaInvest.bat` → **Enviar a** → **Escritorio (crear
acceso directo)**. Podrás renombrarlo a "Balanzia Invest" y cambiarle el icono.

---

> Nota: el lanzador apunta a la rama de desarrollo actual
> (`claude/stock-analysis-investment-tool-rvG42`). Cuando fusiones el PR a
> `main`, puedes editar el `.bat` y poner `set BRANCH=main`.
