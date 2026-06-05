"""Detector de tendencia.

Combina estructura de medias, fuerza (ADX) y posición del precio para emitir
señales alcistas/bajistas explicadas. Trabaja sobre la última fila de un
DataFrame ya enriquecido con indicadores (ver indicators.technical.enrich).
"""
from __future__ import annotations

import pandas as pd

from .base import Signal, SignalGroup


def _last(series: pd.Series) -> float | None:
    if series is None or series.empty:
        return None
    val = series.iloc[-1]
    return None if pd.isna(val) else float(val)


def evaluate(df: pd.DataFrame) -> SignalGroup:
    group = SignalGroup("Tendencia")
    close = _last(df["Close"])
    sma_fast = _last(df.get("sma_fast"))
    sma_slow = _last(df.get("sma_slow"))
    macd_hist = _last(df.get("hist"))
    adx = _last(df.get("adx"))
    plus_di = _last(df.get("plus_di"))
    minus_di = _last(df.get("minus_di"))

    # 1) Precio vs media larga: el filtro de tendencia primaria.
    if close is not None and sma_slow is not None:
        if close > sma_slow:
            group.add(Signal("Precio > SMA200", 0.8, 1.5, "Tendencia primaria alcista (precio sobre la media de 200)."))
        else:
            group.add(Signal("Precio < SMA200", -0.8, 1.5, "Tendencia primaria bajista (precio bajo la media de 200)."))

    # 2) Estructura de medias (golden/death cross).
    if sma_fast is not None and sma_slow is not None:
        if sma_fast > sma_slow:
            group.add(Signal("SMA50 > SMA200", 0.6, 1.0, "Media rápida sobre la lenta: estructura alcista."))
        else:
            group.add(Signal("SMA50 < SMA200", -0.6, 1.0, "Media rápida bajo la lenta: estructura bajista."))

    # 3) Fuerza de tendencia (ADX) con su dirección (DI+/DI-).
    if adx is not None and plus_di is not None and minus_di is not None:
        strength = min(1.0, adx / 40.0)  # ADX>40 = tendencia muy fuerte
        if adx >= 20:
            direction = 1.0 if plus_di > minus_di else -1.0
            sentido = "alcista" if direction > 0 else "bajista"
            group.add(Signal("ADX", direction * strength, 1.2, f"Tendencia {sentido} con fuerza (ADX={adx:.0f})."))
        else:
            group.add(Signal("ADX bajo", 0.0, 0.5, f"Sin tendencia clara (ADX={adx:.0f}, rango lateral)."))

    # 4) Momentum MACD (histograma).
    if macd_hist is not None:
        score = max(-1.0, min(1.0, macd_hist / (abs(macd_hist) + 1e-9)))
        if macd_hist > 0:
            group.add(Signal("MACD", 0.4, 0.8, "Momentum positivo (histograma MACD > 0)."))
        elif macd_hist < 0:
            group.add(Signal("MACD", -0.4, 0.8, "Momentum negativo (histograma MACD < 0)."))

    return group
