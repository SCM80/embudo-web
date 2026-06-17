"""Tests de veracidad: aviso de datos pobres, sentimiento no-US y sin Mag7."""
from __future__ import annotations

import numpy as np
import pandas as pd

from embudo import analyzer, config
from embudo.data import universe, yahoo
from embudo.profiles import PRESETS


def _fake_prices(n):
    idx = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="B")
    c = pd.Series(100 + np.arange(n) * 0.1, index=idx)
    return pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99,
                         "Close": c, "Volume": pd.Series(1e6, index=idx)})


def test_data_warning_when_short_history(monkeypatch):
    config.DEMO_MODE = False
    monkeypatch.setattr(yahoo, "get_prices", lambda *a, **k: _fake_prices(30))   # < 60
    monkeypatch.setattr(yahoo, "get_fundamentals", lambda t: {"name": t, "headlines": []})
    a = analyzer.analyze("AAA", PRESETS["Calidad/Valor (Buffett)"], with_backtest=False)
    assert a.data_warning is not None
    assert a.n_bars == 30


def test_no_warning_with_enough_recent_history(monkeypatch):
    config.DEMO_MODE = False
    monkeypatch.setattr(yahoo, "get_prices", lambda *a, **k: _fake_prices(300))
    monkeypatch.setattr(yahoo, "get_fundamentals", lambda t: {"name": t, "headlines": []})
    a = analyzer.analyze("AAA", PRESETS["Calidad/Valor (Buffett)"], with_backtest=False)
    assert a.data_warning is None


def test_sentiment_not_applicable_for_non_us(monkeypatch):
    config.DEMO_MODE = False
    monkeypatch.setattr(yahoo, "get_prices", lambda *a, **k: _fake_prices(300))
    monkeypatch.setattr(yahoo, "get_fundamentals",
                        lambda t: {"name": t, "headlines": ["Great earnings beat", "Strong growth"]})
    # Valor IBEX (.MC): el sentimiento no debe contar (n=0), titulares ignorados.
    a = analyzer.analyze("SAN.MC", PRESETS["Calidad/Valor (Buffett)"], with_backtest=False)
    assert a.consensus.sentiment.n == 0
    assert "No aplicable" in a.consensus.sentiment.detail
    # En US sí se evalúan.
    us = analyzer.analyze("AAA", PRESETS["Calidad/Valor (Buffett)"], with_backtest=False)
    assert us.consensus.sentiment.n == 2


def test_universe_has_no_magnificent7():
    assert not any("Magnificent" in k for k in universe.UNIVERSES)
    assert not any("Magnificent" in k for k in universe.REGIME_INDEX)
