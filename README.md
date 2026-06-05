# 📊 Embudo — Copiloto de inversión en bolsa

Herramienta **gratuita y sin API keys de pago** para apoyar decisiones de
inversión combinando **análisis técnico**, **contexto de mercado (régimen)**,
una **capa cualitativa** (recomendaciones de analistas + sentimiento de
noticias) y **gestión de riesgo**, con **backtest** para validar las señales en
lugar de creérselas a ciegas.

> ⚠️ **Aviso**: Embudo es una herramienta de **apoyo a la decisión**, *no*
> asesoramiento financiero. Invertir conlleva riesgo de pérdida.

## ✨ Qué hace

- **🧭 Explorar (recomendador):** escanea un universo (IBEX 35, Dow 30, Mag 7) y
  **rankea los mejores candidatos según tu estrategia**.
- **🔬 Analizar (ficha):** análisis completo de un valor con señales
  **explicadas** (el *por qué*, no solo el *qué*).
- **Selector de estrategia en dos ejes:**
  - **Horizonte:** Largo plazo · Intraday · Corto / bajista.
  - **Enfoque:** un slider de *100% técnico ↔ 100% cualitativo* que reajusta los
    pesos del consenso.
- **Régimen de mercado** (semáforo): atenúa señales que reman contra el mercado.
- **Consenso honesto:** no esconde el desacuerdo — si técnico y cualitativo se
  contradicen, baja la confianza y te avisa.
- **Plan de riesgo:** stop por ATR, tamaño de posición por % de capital y R:R.
- **Backtest:** win rate y retorno medio histórico de cada señal.

## 🧱 Fuentes de datos (todas gratis, sin key)

- **Yahoo Finance** vía `yfinance` (precios, analistas, noticias).
- **Stooq** como *fallback* gratuito para datos diarios.
- **VADER** (local) para sentimiento de titulares.

## 🚀 Uso

```bash
pip install -r requirements.txt
streamlit run app.py
```

Abre el navegador en la URL que indica Streamlit (por defecto
`http://localhost:8501`).

## 🧪 Tests

```bash
pip install pytest
pytest -q
```

Los tests validan indicadores, señales, consenso, riesgo y backtest con datos
sintéticos (sin necesidad de red).

## 🗂️ Arquitectura

El **motor de análisis** (`embudo/`) es una librería pura e independiente de la
interfaz; `app.py` (Streamlit) es solo la cara visible. Ver
[`DESIGN.md`](DESIGN.md) para el diseño completo y la hoja de ruta.

```
embudo/
├── data/         # Yahoo + caché + fallback Stooq + universos
├── indicators/   # Indicadores técnicos (pandas/numpy puro)
├── signals/      # Tendencia, volumen y reglas por horizonte
├── qualitative/  # Analistas + sentimiento (VADER)
├── consensus/    # Motor de consenso ponderado y honesto
├── regime.py     # Detector de régimen de mercado
├── risk.py       # Stop / tamaño / R:R
├── backtest.py   # Validación histórica de señales
├── profiles.py   # Perfiles de estrategia (pesos + filtros)
├── screener/     # El recomendador que rankea universos
└── analyzer.py   # Fachada de alto nivel
```
