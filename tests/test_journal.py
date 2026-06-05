"""Tests del diario de operaciones, post-mortem y alertas."""
from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest

from embudo import config


@pytest.fixture
def jrnl(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))
    from embudo import journal
    importlib.reload(journal)
    return journal


def _ohlcv(closes):
    idx = pd.date_range("2022-01-01", periods=len(closes), freq="D")
    c = pd.Series(closes, index=idx)
    return pd.DataFrame({"Open": c.shift(1).fillna(c.iloc[0]), "High": c * 1.01,
                         "Low": c * 0.99, "Close": c, "Volume": pd.Series(1e6, index=idx)})


# --- Trade / journal ---

def test_trade_metrics_long(jrnl):
    t = jrnl.Trade("AAPL", 1, entry=100, stop=95, target=110, shares=10)
    t.status, t.exit = "closed", 110.0
    assert t.r_multiple() == 2.0           # (110-100)/5
    assert t.pnl_pct() == 10.0
    assert t.pnl(commission_pct=0.0) == 100.0
    assert t.followed_plan() is True


def test_trade_metrics_short(jrnl):
    t = jrnl.Trade("XYZ", -1, entry=100, stop=105, target=90, shares=10)
    t.status, t.exit = "closed", 90.0
    assert t.r_multiple() == 2.0           # corto que baja gana
    assert t.pnl(commission_pct=0.0) == 100.0


def test_journal_add_close_persist(jrnl):
    t = jrnl.Trade("AAPL", 1, 100, 95, 110, 10, horizon="Largo plazo")
    jrnl.add(t)
    assert len(jrnl.open_trades()) == 1
    jrnl.close(t.id, 110.0, reason="objetivo")
    assert len(jrnl.open_trades()) == 0
    assert len(jrnl.closed_trades()) == 1
    assert jrnl.closed_trades()[0].exit == 110.0


def test_journal_remove(jrnl):
    t = jrnl.Trade("AAPL", 1, 100, 95, 110, 10)
    jrnl.add(t)
    jrnl.remove(t.id)
    assert jrnl.load() == []


# --- Post-mortem ---

def test_postmortem_empty(jrnl):
    from embudo import postmortem
    s = postmortem.summarize([])
    assert s.n == 0
    assert s.lessons


def test_postmortem_stats(jrnl):
    from embudo import postmortem
    trades = []
    # 2 ganadores de +2R y 1 perdedor de -1R -> esperanza positiva.
    for ex in (110.0, 110.0):
        t = jrnl.Trade("A", 1, 100, 95, 110, 10, horizon="Largo plazo")
        t.status, t.exit = "closed", ex
        trades.append(t)
    loser = jrnl.Trade("B", 1, 100, 95, 110, 10, horizon="Largo plazo")
    loser.status, loser.exit = "closed", 95.0
    trades.append(loser)

    s = postmortem.summarize(trades)
    assert s.n == 3
    assert s.wins == 2 and s.losses == 1
    assert s.avg_r == round((2 + 2 - 1) / 3, 2)
    assert s.profit_factor == 4.0          # 4R ganados / 1R perdido
    assert s.by_horizon["Largo plazo"] == 1.0


# --- Alertas ---

def test_alert_price_above(jrnl):
    from embudo import alerts
    df = _ohlcv(100 + np.arange(250) * 0.1)  # acaba ~124.9
    rule = alerts.AlertRule("AAPL", "price_above", 120)
    assert alerts.evaluate(rule, df).triggered is True
    rule2 = alerts.AlertRule("AAPL", "price_above", 200)
    assert alerts.evaluate(rule2, df).triggered is False


def test_alert_rsi_below(jrnl):
    from embudo import alerts
    df = _ohlcv(200 * (0.99) ** np.arange(250))  # caída -> RSI bajo
    rule = alerts.AlertRule("XYZ", "rsi_below", 40)
    assert alerts.evaluate(rule, df).triggered is True


def test_alert_persist(jrnl, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))
    from embudo import alerts
    importlib.reload(alerts)
    r = alerts.AlertRule("AAPL", "price_below", 90)
    alerts.add(r)
    assert len(alerts.load()) == 1
    alerts.remove(r.id)
    assert alerts.load() == []
