"""Tests del generador de carteras."""
from __future__ import annotations

import pandas as pd

from embudo import portfolio


def _candidates():
    return pd.DataFrame([
        {"ticker": "AAA", "name": "A", "label": "Compra fuerte", "score": 0.6, "price": 100.0, "profit_est": 10},
        {"ticker": "BBB", "name": "B", "label": "Compra", "score": 0.3, "price": 50.0, "profit_est": 6},
        {"ticker": "CCC", "name": "C", "label": "Compra", "score": 0.2, "price": 20.0, "profit_est": 4},
    ])


def test_generate_equal_weight():
    pos = portfolio.generate(_candidates(), capital=9000, n=3, method="equal")
    assert len(pos) == 3
    assert abs(sum(p.weight for p in pos) - 1.0) < 0.02   # pesos redondeados a 3 decimales
    # Equiponderado: 3000 cada uno.
    assert all(abs(p.amount - 3000) < 1 for p in pos)
    # Acciones = importe // precio.
    aaa = next(p for p in pos if p.ticker == "AAA")
    assert aaa.shares == 30


def test_generate_score_weight_favors_strongest():
    pos = portfolio.generate(_candidates(), capital=10000, n=3, method="score")
    w = {p.ticker: p.weight for p in pos}
    assert w["AAA"] > w["BBB"] > w["CCC"]    # más score -> más peso
    assert abs(sum(w.values()) - 1.0) < 1e-6


def test_generate_limits_n():
    pos = portfolio.generate(_candidates(), capital=10000, n=2, method="equal")
    assert len(pos) == 2


def test_generate_skips_without_price():
    df = _candidates()
    df.loc[0, "price"] = None
    pos = portfolio.generate(df, capital=10000, n=3, method="equal")
    assert "AAA" not in [p.ticker for p in pos]


def test_generate_empty():
    assert portfolio.generate(pd.DataFrame(), capital=10000) == []
