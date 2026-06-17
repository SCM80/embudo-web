"""Señales Wyckoff: sacudidas (springs/upthrusts) y fase del rango.

Metodología Wyckoff (Villahermosa): el precio se mueve por la acción del gran
capital. Aquí detectamos dos lecturas de alta calidad sobre los niveles y el
rango:

- **Spring**: el precio perfora un soporte y vuelve a cerrar por encima → sacudida
  bajista fallida = fuerza (alcista).
- **Upthrust**: el precio supera una resistencia y cierra por debajo → ruptura
  alcista fallida = debilidad (bajista).
- **Fase del rango**: en lateral (ADX bajo), el OBV revela acumulación o
  distribución del operador compuesto.
"""
from __future__ import annotations

import pandas as pd

from .base import Signal, SignalGroup


def _last(df: pd.DataFrame, col: str):
    s = df.get(col)
    if s is None or s.dropna().empty:
        return None
    return float(s.dropna().iloc[-1])


def evaluate(df: pd.DataFrame, levels, lookback: int = 5) -> SignalGroup:
    group = SignalGroup("Wyckoff")
    if df is None or len(df) < lookback + 1 or not levels:
        return group

    recent = df.iloc[-lookback:]
    last_close = float(df["Close"].iloc[-1])
    low_min = float(recent["Low"].min())
    high_max = float(recent["High"].max())

    # Spring: perforó un soporte pero recuperó (cierre por encima del nivel).
    for lv in levels:
        if lv.kind == "soporte" and low_min < lv.price <= last_close:
            group.add(Signal("Spring (Wyckoff)", 0.6, 1.3,
                             f"Sacudida bajo el soporte {lv.price:.2f} con recuperación: "
                             f"spring alcista (manos fuertes acumulando)."))
            break

    # Upthrust: superó una resistencia pero cerró por debajo (ruptura fallida).
    for lv in levels:
        if lv.kind == "resistencia" and high_max > lv.price >= last_close:
            group.add(Signal("Upthrust (Wyckoff)", -0.6, 1.3,
                             f"Ruptura fallida de la resistencia {lv.price:.2f}: "
                             f"upthrust bajista (manos fuertes distribuyendo)."))
            break

    # Fase del rango: ADX bajo (lateral) + pendiente del OBV.
    adx = _last(df, "adx")
    obv = df.get("obv")
    if adx is not None and adx < 20 and obv is not None and len(obv.dropna()) > 20:
        o = obv.dropna()
        slope = (o.iloc[-1] - o.iloc[-20]) / (abs(o.iloc[-20]) + 1e-9)
        if slope > 0.05:
            group.add(Signal("Acumulación (rango)", 0.4, 0.9,
                             "Rango lateral con OBV al alza: fase de acumulación (Wyckoff)."))
        elif slope < -0.05:
            group.add(Signal("Distribución (rango)", -0.4, 0.9,
                             "Rango lateral con OBV a la baja: fase de distribución (Wyckoff)."))

    return group
