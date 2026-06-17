"""Detección automática de niveles de soporte y resistencia.

Localiza pivotes (máximos/mínimos locales), agrupa los cercanos en zonas y
mide su "fuerza" por el número de toques. Sirve para dibujar el gráfico, para
afinar stops/objetivos en estructura (mejor que un stop ciego por ATR) y para
detectar rupturas (clave en cortos).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Level:
    price: float
    kind: str        # "soporte" | "resistencia"
    touches: int     # nº de pivotes que forman la zona (fuerza)

    @property
    def strength(self) -> str:
        if self.touches >= 4:
            return "fuerte"
        if self.touches >= 2:
            return "media"
        return "débil"


def _pivots(df: pd.DataFrame, window: int) -> tuple[list[float], list[float]]:
    """Devuelve precios de máximos y mínimos locales (swing points)."""
    highs, lows = [], []
    h, l = df["High"].to_numpy(), df["Low"].to_numpy()
    n = len(df)
    for i in range(window, n - window):
        seg_h, seg_l = h[i - window : i + window + 1], l[i - window : i + window + 1]
        if h[i] == seg_h.max() and (seg_h == h[i]).sum() == 1:
            highs.append(float(h[i]))
        if l[i] == seg_l.min() and (seg_l == l[i]).sum() == 1:
            lows.append(float(l[i]))
    return highs, lows


def _cluster(prices: list[float], tol: float) -> list[tuple[float, int]]:
    """Agrupa precios cercanos (dentro de `tol` relativo) en zonas (precio, toques)."""
    if not prices:
        return []
    prices = sorted(prices)
    clusters: list[list[float]] = [[prices[0]]]
    for p in prices[1:]:
        if abs(p - clusters[-1][-1]) / clusters[-1][-1] <= tol:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return [(float(np.mean(c)), len(c)) for c in clusters]


def detect(df: pd.DataFrame, window: int = 5, tol: float = 0.02, max_levels: int = 6) -> list[Level]:
    """Niveles de S/R ordenados por fuerza, etiquetados respecto al precio actual."""
    if df is None or len(df) < 2 * window + 1:
        return []
    price = float(df["Close"].iloc[-1])
    highs, lows = _pivots(df, window)
    levels: list[Level] = []
    for p, touches in _cluster(highs + lows, tol):
        kind = "resistencia" if p >= price else "soporte"
        levels.append(Level(round(p, 2), kind, touches))
    levels.sort(key=lambda lv: (lv.touches, -abs(lv.price - price)), reverse=True)
    return levels[:max_levels]


def nearest_support(levels: list[Level], price: float) -> Level | None:
    below = [lv for lv in levels if lv.price < price]
    return max(below, key=lambda lv: lv.price) if below else None


def nearest_resistance(levels: list[Level], price: float) -> Level | None:
    above = [lv for lv in levels if lv.price > price]
    return min(above, key=lambda lv: lv.price) if above else None
