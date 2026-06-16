"""Tests de universos dinámicos: fallback, normalización y caché."""
from __future__ import annotations

import importlib

import pytest

from embudo import config


@pytest.fixture
def uni(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(config, "DEMO_MODE", False)
    from embudo.data import universe
    importlib.reload(universe)
    return universe


def test_fallback_when_fetch_fails(uni, monkeypatch):
    # Si la descarga devuelve [] (sin red), usa la lista estática de respaldo.
    monkeypatch.setattr(uni, "_fetch", lambda key: [])
    ibex = uni.get_universe("IBEX 35")
    assert ibex == uni.IBEX35
    assert "SAN.MC" in ibex


def test_fetch_is_cached(uni, monkeypatch):
    calls = {"n": 0}
    def fake_fetch(key):
        calls["n"] += 1
        return ["AAA", "BBB", "CCC"] * 4  # >=10 símbolos
    monkeypatch.setattr(uni, "_fetch", fake_fetch)
    a = uni.get_universe("Dow Jones 30")
    b = uni.get_universe("Dow Jones 30")   # segunda vez: desde caché
    assert a == b
    assert calls["n"] == 1                  # solo se descargó una vez


def test_us_normalization(uni, monkeypatch):
    monkeypatch.setattr(uni, "_fetch", lambda key: [])
    # BRK.B debe quedar como BRK-B (formato Yahoo) vía _norm
    assert uni._norm("BRK.B", "us") == "BRK-B"
    assert uni._norm("aapl", "us") == "AAPL"


def test_ibex_normalization(uni):
    assert uni._norm("SAN", "ibex") == "SAN.MC"
    assert uni._norm("ITX.MC", "ibex") == "ITX.MC"


def test_combined_us_universe(uni, monkeypatch):
    monkeypatch.setattr(uni, "_fetch", lambda key: [])  # fuerza fallback
    us = uni.get_universe("EEUU (Nasdaq 100 + Dow 30)")
    assert len(us) == len(set(us))          # sin duplicados
    assert "AAPL" in us


def test_demo_mode_uses_fallback(uni, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    # En demo no toca red: devuelve el respaldo directamente.
    assert uni.get_universe("S&P 500") == uni.US_LARGE


def test_sp500_in_universes(uni):
    assert "S&P 500" in uni.UNIVERSES
    assert uni.REGIME_INDEX["S&P 500"] == "^GSPC"
