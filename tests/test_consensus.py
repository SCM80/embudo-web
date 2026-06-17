"""Tests del motor de consenso, señales, riesgo y backtest (offline)."""
from __future__ import annotations

from embudo import backtest, risk
from embudo.consensus import engine
from embudo.indicators import technical
from embudo.profiles import PRESETS, StrategyProfile
from embudo.qualitative import analysts, sentiment
from embudo.regime import detect
from embudo.signals import horizons, trend, volume
from embudo.signals.horizons import Horizon


def test_trend_bullish_in_uptrend(uptrend):
    df = technical.enrich(uptrend)
    assert trend.evaluate(df).score > 0.3


def test_trend_bearish_in_downtrend(downtrend):
    df = technical.enrich(downtrend)
    assert trend.evaluate(df).score < -0.3


def test_consensus_label_buy_in_uptrend(uptrend):
    df = technical.enrich(uptrend)
    profile = StrategyProfile(Horizon.LARGO, focus=0.0)  # solo técnico
    cons = engine.evaluate(df, profile)
    assert cons.score > 0
    assert cons.label in ("Compra", "Compra fuerte")
    assert 0.0 <= cons.confidence <= 1.0


def test_consensus_label_sell_in_downtrend(downtrend):
    df = technical.enrich(downtrend)
    profile = StrategyProfile(Horizon.LARGO, focus=0.0)
    cons = engine.evaluate(df, profile)
    assert cons.score < 0
    assert cons.label in ("Venta", "Venta fuerte")


def test_analyst_mean_mapping():
    assert analysts.from_mean(1.0).score == 1.0      # Strong Buy
    assert analysts.from_mean(3.0).score == 0.0      # Hold
    assert analysts.from_mean(5.0).score == -1.0     # Strong Sell
    assert analysts.from_mean(None).score == 0.0     # sin datos


def test_sentiment_degrades_without_headlines():
    view = sentiment.analyze([])
    assert view.n == 0
    assert sentiment.to_signal(view).weight == 0.0


def test_conflict_detected():
    # Técnico alcista fuerte pero analistas muy bajistas -> debe avisar.
    profile = StrategyProfile(Horizon.LARGO, focus=0.5)
    dim = {"tecnico": 0.8, "analistas": -0.8, "sentimiento": 0.0}
    conf, conflict = engine._confidence(dim, {"tecnico": 0.5, "analistas": 0.5, "sentimiento": 0.0})
    assert conflict is not None


def test_regime_bias_multiplier():
    bull = detect_dummy(0.8, "Alcista")
    # Señal bajista en mercado alcista -> atenuada (<1).
    assert bull.bias_multiplier(-0.5) < 1.0
    # Señal alcista en mercado alcista -> intacta.
    assert bull.bias_multiplier(0.5) == 1.0


def detect_dummy(score, label):
    from embudo.regime import Regime
    return Regime(label, "green", score, "test")


def test_risk_plan_long():
    plan = risk.build_plan(entry=100.0, atr=2.0, direction=1, capital=10_000)
    assert plan is not None
    assert plan.stop < plan.entry < plan.target
    assert plan.reward_risk > 0
    assert plan.shares > 0


def test_risk_plan_short():
    plan = risk.build_plan(entry=100.0, atr=2.0, direction=-1, capital=10_000)
    assert plan.target < plan.entry < plan.stop


def test_risk_plan_invalid():
    assert risk.build_plan(entry=100.0, atr=0.0, direction=1, capital=10_000) is None


def test_backtest_runs(uptrend):
    profile = StrategyProfile(Horizon.LARGO, focus=0.0)
    result = backtest.run(uptrend, profile, horizon_bars=10)
    assert result.n_signals >= 0
    assert 0.0 <= result.win_rate <= 1.0


def test_presets_have_valid_weights():
    for name, profile in PRESETS.items():
        w = profile.weights
        assert abs(sum(w.values()) - 1.0) < 1e-6, name
