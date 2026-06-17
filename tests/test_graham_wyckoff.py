"""Tests de los criterios Graham (valor) y Wyckoff (precio-volumen)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from embudo.levels import Level
from embudo.qualitative import fundamentals
from embudo.signals import wyckoff


def _ohlcv(closes, highs=None, lows=None, vols=None):
    n = len(closes)
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    c = pd.Series(closes, index=idx)
    return pd.DataFrame({
        "Open": c.shift(1).fillna(c.iloc[0]),
        "High": pd.Series(highs if highs is not None else c * 1.01, index=idx),
        "Low": pd.Series(lows if lows is not None else c * 0.99, index=idx),
        "Close": c,
        "Volume": pd.Series(vols if vols is not None else np.full(n, 1e6), index=idx),
    })


# --- Graham ---

def test_graham_margin_of_safety_detected():
    # EPS 10, VC 10 -> Nº Graham = sqrt(22.5*10*10)=47.4. Precio 40 < 47.4 -> margen.
    fund = {"trailing_eps": 10, "book_value": 10}
    v = fundamentals.evaluate(fund, price=40)
    assert "Margen de seguridad" in [s.name for s in v.group.signals]
    assert v.score > 0


def test_graham_overvalued_detected():
    # Nº Graham 47.4, precio 80 -> muy por encima -> sobrevalorado.
    fund = {"trailing_eps": 10, "book_value": 10}
    v = fundamentals.evaluate(fund, price=80)
    assert "Sobrevalorado (Graham)" in [s.name for s in v.group.signals]


def test_graham_combined_rule():
    # PER 10 * P/B 1.5 = 15 <= 22.5 -> atractiva
    v = fundamentals.evaluate({"trailing_pe": 10, "price_to_book": 1.5})
    assert "PER×P/B ≤ 22,5" in [s.name for s in v.group.signals]


def test_graham_current_ratio():
    v = fundamentals.evaluate({"current_ratio": 2.5})
    assert "Balance sólido" in [s.name for s in v.group.signals]
    v2 = fundamentals.evaluate({"current_ratio": 0.7})
    assert "Liquidez ajustada" in [s.name for s in v2.group.signals]


def test_graham_no_data_no_signal():
    v = fundamentals.evaluate({}, price=None)
    assert v.n_metrics == 0


# --- Wyckoff ---

def test_wyckoff_spring():
    # Soporte en 100; última sesión perfora a 96 (Low) pero cierra en 101.
    closes = list(np.linspace(110, 102, 10)) + [101.0]
    lows = [c * 0.99 for c in closes[:-1]] + [96.0]
    df = _ohlcv(closes, lows=lows)
    levels = [Level(100.0, "soporte", 3)]
    g = wyckoff.evaluate(df, levels)
    assert "Spring (Wyckoff)" in [s.name for s in g.signals]


def test_wyckoff_upthrust():
    # Resistencia en 100; última sesión supera a 104 (High) pero cierra en 99.
    closes = list(np.linspace(90, 98, 10)) + [99.0]
    highs = [c * 1.01 for c in closes[:-1]] + [104.0]
    df = _ohlcv(closes, highs=highs)
    levels = [Level(100.0, "resistencia", 3)]
    g = wyckoff.evaluate(df, levels)
    assert "Upthrust (Wyckoff)" in [s.name for s in g.signals]


def test_wyckoff_no_levels_no_signal():
    df = _ohlcv(list(np.linspace(100, 110, 30)))
    assert wyckoff.evaluate(df, []).signals == []
