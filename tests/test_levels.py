"""Tests de niveles de soporte/resistencia, VWAP y riesgo en estructura."""
from __future__ import annotations

import numpy as np
import pandas as pd

from embudo import levels, risk
from embudo.indicators import technical


def _ohlcv(closes):
    idx = pd.date_range("2022-01-01", periods=len(closes), freq="D")
    c = pd.Series(closes, index=idx)
    return pd.DataFrame({"Open": c.shift(1).fillna(c.iloc[0]), "High": c * 1.01,
                         "Low": c * 0.99, "Close": c, "Volume": pd.Series(1e6, index=idx)})


def test_levels_detected_on_oscillation():
    # Serie que oscila entre ~90 y ~110 -> debe encontrar soporte y resistencia.
    n = 300
    closes = 100 + 10 * np.sin(np.arange(n) / 6)
    df = _ohlcv(closes)
    lv = levels.detect(df)
    assert len(lv) > 0
    assert any(l.kind == "soporte" for l in lv) or any(l.kind == "resistencia" for l in lv)


def test_levels_classified_by_price():
    n = 300
    closes = 100 + 10 * np.sin(np.arange(n) / 6)
    df = _ohlcv(closes)
    price = float(df["Close"].iloc[-1])
    lv = levels.detect(df)
    for l in lv:
        if l.kind == "soporte":
            assert l.price < price
        else:
            assert l.price >= price


def test_nearest_support_resistance():
    lv = [levels.Level(90, "soporte", 3), levels.Level(95, "soporte", 2),
          levels.Level(110, "resistencia", 4)]
    assert levels.nearest_support(lv, 100).price == 95
    assert levels.nearest_resistance(lv, 100).price == 110


def test_levels_empty_on_short_series():
    df = _ohlcv([100, 101, 102])
    assert levels.detect(df) == []


def test_vwap_positive_and_aligned():
    n = 60
    closes = 100 + np.arange(n) * 0.1
    df = _ohlcv(closes)
    vwap = technical.vwap(df).dropna()
    assert (vwap > 0).all()
    # En tendencia alcista suave, el precio acaba en/por encima del VWAP (tolerancia float).
    assert df["Close"].iloc[-1] >= vwap.iloc[-1] - 1e-6


def test_enrich_includes_vwap():
    df = _ohlcv(100 + np.sin(np.arange(250) / 5))
    assert "vwap" in technical.enrich(df).columns


def test_risk_structure_stop_long():
    # Stop en soporte (98) en vez de ATR: debe quedar justo por debajo de 98.
    plan = risk.build_plan(entry=100.0, atr=5.0, direction=1, capital=10_000,
                           structure_stop=98.0, structure_target=110.0)
    assert plan is not None
    assert 97.5 < plan.stop < 98.0
    assert plan.target == 110.0


def test_risk_structure_stop_ignored_if_wrong_side():
    # Un "soporte" por encima de la entrada no es válido para un largo -> usa ATR.
    plan = risk.build_plan(entry=100.0, atr=2.0, direction=1, capital=10_000,
                           structure_stop=105.0)
    assert plan.stop < 100.0  # cae al stop por ATR
