"""Tests del termómetro de mercado (VIX + contexto)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from embudo import config, market
from embudo.data import yahoo


def test_vix_reading_levels():
    assert market.vix_reading(10)[0] == "Calma"
    assert market.vix_reading(20)[0] == "Normal"
    assert market.vix_reading(28)[0] == "Miedo"
    assert market.vix_reading(35)[0] == "Pánico"
    assert market.vix_reading(None)[0] == "—"


def test_vix_score_monotonic():
    assert market._vix_score(10) > market._vix_score(20) > market._vix_score(28) > market._vix_score(35)


def test_market_context_demo():
    config.DEMO_MODE = True
    try:
        ctx = market.market_context()
        assert ctx.vix is not None
        assert ctx.regime is not None
        assert ctx.clima_label in ("Favorable", "Mixto", "Adverso")
        assert ctx.clima_color in ("green", "orange", "red")
    finally:
        config.DEMO_MODE = False


def test_market_context_survives_missing_data(monkeypatch):
    config.DEMO_MODE = False
    monkeypatch.setattr(yahoo, "get_prices", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(yahoo, "get_fundamentals", lambda t: {"headlines": []})
    ctx = market.market_context()              # no debe romper sin datos
    assert ctx.vix is None
    assert ctx.clima_label in ("Favorable", "Mixto", "Adverso")


def test_breadth_shifts_clima():
    config.DEMO_MODE = True
    try:
        low = market.market_context(breadth=0.0).clima_label
        high = market.market_context(breadth=1.0)
        # Con amplitud alta el clima nunca debe ser peor que con amplitud baja.
        assert high.clima_label in ("Favorable", "Mixto", "Adverso")
    finally:
        config.DEMO_MODE = False
