# 📊 Embudo — Copiloto de inversión en bolsa

Herramienta **gratuita y sin API keys de pago** para apoyar decisiones de
inversión combinando **análisis técnico**, **contexto de mercado (régimen)**,
una **capa cualitativa** (recomendaciones de analistas + sentimiento de
noticias) y **gestión de riesgo**, con **backtest** para validar las señales en
lugar de creérselas a ciegas.

> ⚠️ **Aviso**: Embudo es una herramienta de **apoyo a la decisión**, *no*
> asesoramiento financiero. Invertir conlleva riesgo de pérdida.

## ✨ Qué hace

- **🧭 Recomendador estrategia-first:** eliges **1 de 4 estrategias** y un
  **mercado (IBEX 35 / EEUU Nasdaq 100 + Dow 30 / tu watchlist)**, y Embudo
  **filtra y rankea** las acciones recomendadas. Pinchas una y ves su ficha.
- **4 estrategias:** Calidad/Valor (Buffett), Seguir volumen/momentum, Intraday
  técnico y Posicionarse a corto/bajista.
- **🏛️ Capa fundamental (Buffett):** ROE, deuda, márgenes, PER vs crecimiento.
- **⏱️ Casi tiempo real:** auto-refresco configurable (datos Yahoo con ~15 min de
  retardo) y **clave Finnhub opcional y gratuita** para cotización EEUU más fresca.
- **KPIs** sobre el gráfico: precio y cambio %, capitalización, PER, ROE, rango
  52 semanas y volumen relativo.
- **🔬 Analizar (ficha):** análisis completo de un valor con señales
  **explicadas** (el *por qué*, no solo el *qué*).
- **Selector de estrategia en dos ejes:**
  - **Horizonte:** Largo plazo · Intraday · Corto / bajista.
  - **Enfoque:** un slider de *100% técnico ↔ 100% cualitativo* que reajusta los
    pesos del consenso.
- **Régimen de mercado** (semáforo): atenúa señales que reman contra el mercado.
- **Consenso honesto:** no esconde el desacuerdo — si técnico y cualitativo se
  contradicen, baja la confianza y te avisa.
- **Plan de riesgo:** stop por ATR **o anclado en soporte/resistencia**, tamaño
  de posición por % de capital y R:R.
- **Backtest:** win rate y retorno medio histórico de cada señal.
- **Niveles de soporte/resistencia automáticos** dibujados en el gráfico.
- **VWAP** en intraday y detección de **ruptura de soporte** en cortos.
- **⭐ Watchlist propia persistente** usable como universo en el screener.
- **Exportación a CSV** de los resultados del recomendador.
- **📓 Diario de operaciones + post-mortem**: registra trades con su tesis y
  obtén tu estadística real (win rate, esperanza en R, profit factor, disciplina
  y lecciones sobre tus errores).
- **🔔 Alertas** bajo demanda (precio, RSI, cruce de SMA200), sin coste.
- **Backtest con comisiones** para retornos más realistas.

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
├── qualitative/  # Analistas + sentimiento (VADER) + fundamentales (Buffett)
├── consensus/    # Motor de consenso ponderado y honesto
├── regime.py     # Detector de régimen de mercado
├── levels.py     # Soporte/resistencia automáticos
├── risk.py       # Stop / tamaño / R:R (ATR o estructura)
├── backtest.py   # Validación histórica de señales (con comisiones)
├── profiles.py   # Perfiles de estrategia (pesos + filtros)
├── screener/     # El recomendador que rankea universos
├── watchlist.py  # Watchlist propia persistente
├── journal.py    # Diario de operaciones
├── postmortem.py # Estadística y lecciones del diario
├── alerts.py     # Alertas bajo demanda
└── analyzer.py   # Fachada de alto nivel
```
