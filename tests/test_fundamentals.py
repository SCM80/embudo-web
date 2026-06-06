"""Tests de la capa fundamental (Buffett) y su entrada en el consenso."""
from __future__ import annotations

from embudo.consensus import engine
from embudo.data import universe
from embudo.indicators import technical
from embudo.profiles import DIMENSIONS, PRESETS, StrategyProfile
from embudo.qualitative import fundamentals
from embudo.signals.horizons import Horizon


# --- Scoring fundamental ---

def test_quality_company_scores_high():
    fund = {"roe": 0.25, "debt_to_equity": 30, "profit_margins": 0.22,
            "trailing_pe": 14, "revenue_growth": 0.18}
    view = fundamentals.evaluate(fund)
    assert view.score > 0.4
    assert view.n_metrics == 5
    assert fundamentals.to_signal(view).weight > 0


def test_weak_company_scores_low():
    fund = {"roe": 0.02, "debt_to_equity": 250, "profit_margins": -0.05,
            "trailing_pe": 60, "revenue_growth": -0.10}
    view = fundamentals.evaluate(fund)
    assert view.score < 0


def test_fundamentals_degrade_without_data():
    view = fundamentals.evaluate(None)
    assert view.n_metrics == 0
    assert view.score == 0.0
    assert fundamentals.to_signal(view).weight == 0.0


def test_high_pe_excused_by_growth():
    s = fundamentals._pe_signal(40, 0.20)   # PER alto pero crece >15%
    assert s is not None and s.score >= 0
    s2 = fundamentals._pe_signal(40, 0.0)   # PER alto sin crecimiento -> penaliza
    assert s2.score < 0


# --- Integración con el consenso ---

def test_fundamental_dimension_enters_consensus(uptrend):
    df = technical.enrich(uptrend)
    profile = PRESETS["Calidad/Valor (Buffett)"]
    good = fundamentals.evaluate({"roe": 0.25, "debt_to_equity": 20,
                                  "profit_margins": 0.2, "trailing_pe": 12,
                                  "revenue_growth": 0.2})
    cons = engine.evaluate(df, profile, fundamental_view=good)
    assert "fundamental" in cons.dimension_scores
    assert cons.dimension_scores["fundamental"] > 0
    assert cons.fundamental is not None


def test_no_fundamental_data_does_not_break(uptrend):
    df = technical.enrich(uptrend)
    profile = PRESETS["Calidad/Valor (Buffett)"]
    cons = engine.evaluate(df, profile)   # sin fundamental_view
    assert cons.dimension_scores["fundamental"] == 0.0


# --- Perfiles y universos ---

def test_all_presets_weights_sum_to_one():
    for name, p in PRESETS.items():
        w = p.weights
        assert set(w.keys()) == set(DIMENSIONS), name
        assert abs(sum(w.values()) - 1.0) < 1e-6, name


def test_buffett_weights_fundamental_heavy():
    w = PRESETS["Calidad/Valor (Buffett)"].weights
    assert w["fundamental"] >= 0.4


def test_adhoc_profile_focus_weights_sum_to_one():
    p = StrategyProfile(Horizon.LARGO, focus=0.5)
    assert abs(sum(p.weights.values()) - 1.0) < 1e-6


def test_volume_emphasis_flag():
    assert PRESETS["Seguir volumen/momentum"].volume_emphasis is True


def test_nasdaq100_universe_present():
    assert "EEUU (Nasdaq 100 + Dow 30)" in universe.UNIVERSES
    assert len(universe.UNIVERSES["EEUU (Nasdaq 100 + Dow 30)"]) > 100
    # Sin duplicados
    us = universe.UNIVERSES["EEUU (Nasdaq 100 + Dow 30)"]
    assert len(us) == len(set(us))
