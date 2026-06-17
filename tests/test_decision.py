"""Tests del decisor fácil (semáforo OPERAR / ESPERAR / EVITAR)."""
from __future__ import annotations

from embudo import decision


def test_strong_long_is_operar():
    v = decision.decide(score=0.6, direction=1, profit_pct=8.0, rr=2.0, confidence=0.8)
    assert v.action == "OPERAR" and v.color == "green"
    assert "+8.0%" in v.phrase


def test_neutral_is_esperar():
    v = decision.decide(score=0.05, direction=1, profit_pct=3.0, rr=1.5, confidence=0.7)
    assert v.action == "ESPERAR" and v.color == "orange"


def test_bearish_long_is_evitar():
    v = decision.decide(score=-0.4, direction=1, profit_pct=2.0, rr=1.2, confidence=0.6)
    assert v.action == "EVITAR" and v.color == "red"


def test_strong_short_is_operar():
    # Para un corto, un score muy negativo es una gran oportunidad.
    v = decision.decide(score=-0.6, direction=-1, profit_pct=7.0, rr=2.0, confidence=0.8)
    assert v.action == "OPERAR"
    assert "PONERSE CORTO" in v.phrase.upper()


def test_bullish_value_bad_for_short_is_evitar():
    # Valor alcista (score +0.4) en estrategia de corto -> evitar.
    v = decision.decide(score=0.4, direction=-1, profit_pct=2.0, rr=1.0, confidence=0.6)
    assert v.action == "EVITAR"


def test_handles_missing_profit():
    v = decision.decide(score=0.6, direction=1, profit_pct=None, rr=None, confidence=0.5)
    assert v.action == "OPERAR" and "—" in v.phrase
