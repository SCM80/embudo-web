"""Tests del seguimiento 'forward': precio/fecha/estrategia de fijación y migración."""
from __future__ import annotations

import importlib
import json

import pytest

from embudo import config


@pytest.fixture
def wl(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))
    from embudo import watchlist
    importlib.reload(watchlist)
    return watchlist


def test_add_with_price_and_strategy(wl):
    wl.add("aapl", price=100.0, strategy="Calidad/Valor (Buffett)")
    e = wl.entries()[0]
    assert e["ticker"] == "AAPL"
    assert e["pin_price"] == 100.0
    assert e["strategy"] == "Calidad/Valor (Buffett)"
    assert e["pin_date"]              # fecha de hoy
    assert wl.tickers() == ["AAPL"]


def test_backward_compat_load_returns_tickers(wl):
    wl.add("AAPL", price=10)
    wl.add("MSFT", price=20)
    assert wl.load() == ["AAPL", "MSFT"]      # load() sigue dando tickers


def test_migration_from_old_list(wl, tmp_path):
    # Formato antiguo: lista de strings. Debe migrar sin perder nada.
    (tmp_path / "watchlist.json").write_text(json.dumps(["AAPL", "SAN.MC"]), encoding="utf-8")
    importlib.reload(wl)
    ents = wl.entries()
    assert [e["ticker"] for e in ents] == ["AAPL", "SAN.MC"]
    assert all(e["pin_price"] is None for e in ents)


def test_set_price_for_migrated(wl, tmp_path):
    (tmp_path / "watchlist.json").write_text(json.dumps(["AAPL"]), encoding="utf-8")
    importlib.reload(wl)
    wl.set_price("AAPL", 150.0, strategy="Intraday técnico")
    e = wl.entries()[0]
    assert e["pin_price"] == 150.0
    assert e["strategy"] == "Intraday técnico"


def test_no_duplicates_and_remove(wl):
    wl.add("AAPL", price=1)
    wl.add("aapl", price=2)          # duplicado
    assert wl.tickers() == ["AAPL"]
    wl.remove("AAPL")
    assert wl.tickers() == []
