# 📐 Balanzia Invest — Diseño técnico y hoja de ruta

## Visión

De un *"oráculo que dice compra/vende"* a un **copiloto de decisión con gestión
de riesgo y memoria**. La ventaja real no está en predecir mejor, sino en el
**proceso**: filtrar sistemáticamente, imponer disciplina de riesgo y validar
las señales con datos históricos.

## Principios de diseño

1. **Evidencia > intuición** → toda señal mostrada se puede backtestear.
2. **Proceso > predicción** → el edge está en el riesgo y la consistencia.
3. **Contexto top-down** → el régimen de mercado pesa más que un indicador suelto.
4. **No esconder el desacuerdo** → si las fuentes se contradicen, se avisa.
5. **Riesgo primero** → ninguna entrada sin su salida (stop + tamaño + R:R).
6. **Explicabilidad** → mostrar *qué reglas se dispararon*, no una caja negra.
7. **Robustez > complejidad** → pocos indicadores robustos, sin sobreoptimizar.
8. **Motor desacoplado de la UI** → librería pura testeable; Streamlit es la cara.
9. **Gratis y resiliente** → solo fuentes sin coste, con caché y fallback.

## Stack

| Capa | Elección | Motivo |
|------|----------|--------|
| Lenguaje | Python 3.11 | Mejor ecosistema financiero. |
| UI | Streamlit | Dashboard web sin backend/hosting de pago. |
| Datos | `yfinance` + Stooq (fallback) | Gratis, sin API key. |
| Indicadores | pandas/numpy puro | Sin compilar (sin TA-Lib), testeable offline. |
| Gráficos | Plotly | Velas + volumen interactivos. |
| Sentimiento | VADER local | Sin API, sin coste. |

## Flujo de decisión

```
1. Régimen de mercado (semáforo global)     ← contexto primero
2. Screener por perfil de estrategia        ← rankea candidatos
3. Ficha del valor con señales EXPLICADAS   ← el porqué
4. Backtest de la señal                     ← ¿ha ganado dinero?
5. Plan de trade: stop + tamaño + R:R       ← riesgo antes de entrar
6. (Roadmap) Diario + post-mortem           ← cerrar el bucle
```

## Modelo de consenso

Cada dimensión produce un score en `[-1, +1]`:

- **Técnico**: tendencia (SMA/ADX/MACD) + volumen (OBV/vol. relativo/divergencias)
  + reglas por horizonte (RSI, cruces EMA, Bollinger).
- **Analistas**: `recommendationMean` de Yahoo (1..5) → `[-1, +1]`.
- **Sentimiento**: VADER sobre titulares.

```
combinado = Σ (score_dim · peso_dim) / Σ pesos   (solo dimensiones con datos)
combinado ·= multiplicador_de_régimen            (atenúa remar contra el mercado)
```

- **Confianza** = `1 − dispersión` entre dimensiones; penalizada si hay
  conflicto de signos (y se muestra un aviso explícito).
- **Degradación elegante**: sin analistas/noticias, esas dimensiones pesan 0.

## Perfiles de estrategia (dos ejes)

- **Horizonte** → elige intervalo/periodo de datos y reglas técnicas:
  Largo (`1d`/2y), Intraday (`15m`/60d), Corto/bajista (`1d`/1y, busca ventas).
- **Enfoque** (`focus` 0→1) → reparte peso técnico ↔ cualitativo.

## Gestión de riesgo

- Stop a `N · ATR` de la entrada (por defecto 2·ATR).
- Tamaño de posición para arriesgar un % fijo del capital (por defecto 1%).
- Objetivo según R:R (por defecto 2R). Si el R:R es malo, la operación se descarta.

## Backtest (test de cordura)

Recorre el histórico, dispara la señal técnica del perfil y mide el retorno
*forward* a N barras → win rate, retorno medio y nº de señales. Sin comisiones
ni slippage: es validación honesta, no un motor de trading profesional.

## Limitaciones conocidas

- `yfinance` es no oficial y tiene **rate-limit**: por eso caché + universos pequeños.
- Intraday de Yahoo viene **con retardo** (no apto para scalping en vivo).
- Campos de analistas/noticias a veces vacíos → degradación automática.
- El backtest es simplificado (sin costes, una posición a la vez).

## Hoja de ruta

- **Fase 1 (hecha):** datos + indicadores + régimen + consenso honesto + ficha
  explicada + perfiles + screener + riesgo + backtest mínimo + tests.
- **Fase 2 (hecha):** niveles de soporte/resistencia automáticos (+ stops en
  estructura), VWAP en intraday, ruptura de soporte en cortos, watchlist propia
  persistente (universo en el screener) y exportación de resultados a CSV.
- **Fase 3 (hecha):** **diario de operaciones + post-mortem** (cerrar el bucle de
  aprendizaje), **alertas** bajo demanda y **backtest con comisiones**.
- **v3 (hecha):** recomendador **estrategia-first** (4 estrategias) acotado a
  **IBEX + EEUU (Nasdaq 100 + Dow 30)**, **capa fundamental (Buffett)**,
  cabecera de **KPIs**, cotización **casi-real** (auto-refresco + clave Finnhub
  opcional) y ficha con porqués técnico + fundamental + analistas + noticias.

### Detalle v3
- `qualitative/fundamentals.py`: score de calidad/valor (ROE, deuda, márgenes,
  PER vs crecimiento) con sub-señales explicadas; degrada con peso 0 sin datos.
- `data/realtime.py`: `get_live_quote()` → Finnhub (clave gratis opcional) o
  Yahoo `fast_info` con sello de hora y aviso de retardo.
- `data/universe.py`: añadidos `NASDAQ100` y "EEUU (Nasdaq 100 + Dow 30)".
- `profiles.py`: 4 presets con pesos explícitos sobre {tecnico, fundamental,
  analistas, sentimiento}; `volume_emphasis` para "Seguir volumen/momentum".
- `consensus/engine.py`: nueva dimensión **fundamental** (mantiene confianza y
  aviso de desacuerdo).
- `app.py`: flujo estrategia → lista → ficha; KPIs; auto-refresco opcional.

### Criterio avanzado (Graham & Wyckoff)
- **Graham** (`qualitative/fundamentals.py`): Número de Graham (margen de
  seguridad: precio vs √(22,5·BPA·VC)), regla PER×P/B ≤ 22,5 y current ratio.
- **Wyckoff** (`signals/wyckoff.py` + `signals/volume.py`): springs/upthrusts
  (sacudidas en soportes/resistencias), fase del rango (acumulación/distribución
  por OBV), esfuerzo vs resultado y volumen climático.
- **Anti-sobreextensión** (`signals/trend.py`): penaliza comprar muy por encima
  de la media; **caída brusca** reciente como aviso de distribución.

### Fuera de alcance (decidido con el usuario)
- Sentimiento de redes sociales (cobertura nula en IBEX; descartado).
- Tiempo real de pago, ejecución de órdenes o conexión con bróker.

### Detalle Fase 3

- **Diario** (`journal.py`): registra cada operación con su *tesis*; al cerrarla
  calcula P&L (neto de comisiones), R-múltiplo y si se respetó el plan.
- **Post-mortem** (`postmortem.py`): win rate, esperanza en R, profit factor,
  disciplina (% de planes respetados), R por horizonte y **lecciones** sobre los
  propios errores.
- **Alertas** (`alerts.py`): reglas (precio, RSI, cruce de SMA200) evaluadas bajo
  demanda contra los datos actuales — sin servicio en segundo plano, coste cero.
- **Backtest con comisiones**: descuento de ida y vuelta (5 pb por lado por
  defecto) para un retorno más realista.
