# 📐 Embudo — Diseño técnico y hoja de ruta

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
- **Fase 2:** afinar intraday/corto, niveles soporte/resistencia automáticos,
  watchlist propia persistente, exportar resultados.
- **Fase 3:** **diario de operaciones + post-mortem** (cerrar el bucle de
  aprendizaje), alertas y backtest con costes/comisiones.
