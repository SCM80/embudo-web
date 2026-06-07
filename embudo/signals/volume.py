"""Análisis de volumen y divergencias precio-volumen.

El volumen confirma (o desmiente) el movimiento del precio. Aquí detectamos
volumen relativo anómalo, la tendencia del OBV y divergencias precio/OBV.
"""
from __future__ import annotations

import pandas as pd

from .base import Signal, SignalGroup


def _slope(series: pd.Series, window: int) -> float | None:
    """Pendiente normalizada del tramo final (signo + magnitud relativa)."""
    s = series.dropna()
    if len(s) < window:
        return None
    tail = s.iloc[-window:]
    change = tail.iloc[-1] - tail.iloc[0]
    denom = tail.abs().mean() + 1e-9
    return float(change / denom)


def evaluate(df: pd.DataFrame, window: int = 20) -> SignalGroup:
    group = SignalGroup("Volumen")

    # 1) Volumen relativo de la última sesión.
    rel_vol = df.get("rel_volume")
    if rel_vol is not None and not rel_vol.dropna().empty:
        rv = float(rel_vol.dropna().iloc[-1])
        price_chg = float(df["Close"].pct_change().iloc[-1]) if len(df) > 1 else 0.0
        if rv >= 1.5:
            direction = 1.0 if price_chg >= 0 else -1.0
            sentido = "compradora" if direction > 0 else "vendedora"
            group.add(Signal("Volumen alto", direction * 0.6, 1.0, f"Volumen {rv:.1f}x lo normal con presión {sentido}."))
        elif rv < 0.6:
            group.add(Signal("Volumen flojo", 0.0, 0.4, f"Volumen bajo ({rv:.1f}x): movimiento poco fiable."))

    # 2) Tendencia del OBV (acumulación / distribución).
    obv = df.get("obv")
    obv_slope = _slope(obv, window) if obv is not None else None
    if obv_slope is not None:
        if obv_slope > 0.05:
            group.add(Signal("OBV alcista", 0.5, 1.0, "OBV en ascenso: acumulación (entra dinero)."))
        elif obv_slope < -0.05:
            group.add(Signal("OBV bajista", -0.5, 1.0, "OBV en descenso: distribución (sale dinero)."))

    # 3) Divergencia precio vs OBV (la señal más valiosa de esta dimensión).
    price_slope = _slope(df["Close"], window)
    if price_slope is not None and obv_slope is not None:
        if price_slope > 0.02 and obv_slope < -0.02:
            group.add(Signal("Divergencia bajista", -0.7, 1.3, "Precio sube pero el volumen no acompaña: posible techo."))
        elif price_slope < -0.02 and obv_slope > 0.02:
            group.add(Signal("Divergencia alcista", 0.7, 1.3, "Precio baja pero hay acumulación: posible suelo."))

    # Caída brusca en la última sesión = posible distribución / giro.
    if len(df) > 1:
        ret1 = float(df["Close"].pct_change().iloc[-1])
        rv_last = float(rel_vol.dropna().iloc[-1]) if rel_vol is not None and not rel_vol.dropna().empty else 1.0
        if ret1 <= -0.07:
            extra = " con volumen alto (distribución)" if rv_last >= 1.3 else ""
            group.add(Signal("Caída brusca reciente", -0.6, 1.2,
                             f"Caída de {ret1*100:.0f}% en la última sesión{extra}: posible giro, cautela."))

    return group
