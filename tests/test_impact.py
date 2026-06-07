"""Tests de validación del score, cartera y conversión de divisa."""
from __future__ import annotations

import numpy as np
import pandas as pd

from embudo import portfolio, risk, validation


def _series(closes):
    idx = pd.date_range("2020-01-01", periods=len(closes), freq="D")
    c = pd.Series(closes, index=idx)
    return pd.DataFrame({"Open": c.shift(1).fillna(c.iloc[0]), "High": c * 1.01,
                         "Low": c * 0.99, "Close": c, "Volume": pd.Series(1e6, index=idx)})


# --- Validación ---

def test_validation_runs_and_buckets():
    # Tendencia alcista clara -> debe haber observaciones y, idealmente, correlación >= 0.
    up = _series(100 * (1.002) ** np.arange(400))
    res = validation.validate({"A": up}, horizon_bars=10, step=10, warmup=200)
    assert res.n_obs > 0
    assert -1.0 <= res.correlation <= 1.0
    assert res.verdict


def test_validation_insufficient_data():
    res = validation.validate({"A": _series([100, 101, 102])})
    assert res.n_obs == 0
    assert "insuficientes" in res.verdict.lower()


# --- Cartera ---

def test_portfolio_exposure_and_concentration():
    from embudo.journal import Trade
    trades = [Trade("AAPL", 1, entry=100, stop=95, target=110, shares=30),   # 3000
             Trade("MSFT", 1, entry=200, stop=190, target=220, shares=5)]    # 1000
    pv = portfolio.summarize(trades, capital=10000)
    assert len(pv.positions) == 2
    assert abs(pv.gross_exposure - 0.40) < 1e-6        # 4000/10000
    # AAPL pesa 30% > 25% -> aviso
    assert any("AAPL" in w for w in pv.warnings)


def test_portfolio_net_exposure_with_short():
    from embudo.journal import Trade
    trades = [Trade("A", 1, 100, 95, 110, 10),    # +1000 largo
             Trade("B", -1, 100, 105, 90, 10)]    # -1000 corto
    pv = portfolio.summarize(trades, capital=10000)
    assert abs(pv.net_exposure) < 1e-6              # se compensan


def test_correlations_detects_high():
    base = np.cumsum(np.random.default_rng(1).normal(0, 1, 200))
    a = _series(100 + base)
    b = _series(100 + base + np.random.default_rng(2).normal(0, 0.05, 200))  # casi idéntica
    pairs = portfolio.correlations({"A": a, "B": b}, threshold=0.7)
    assert pairs and pairs[0][2] >= 0.7


# --- FX en el sizing ---

def test_fx_reduces_shares_for_usd():
    # Mismo riesgo por accion; con fx<1 (USD->EUR) las acciones cambian de forma coherente.
    eur = risk.build_plan(entry=100, atr=2, direction=1, capital=10000, fx=1.0)
    usd = risk.build_plan(entry=100, atr=2, direction=1, capital=10000, fx=0.9)
    assert eur.shares != usd.shares
    # Con fx=0.9 cada accion "cuesta" menos en EUR -> caben mas acciones
    assert usd.shares >= eur.shares
