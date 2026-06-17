"""Tests de la watchlist persistente (con CACHE_DIR temporal)."""
from __future__ import annotations

import importlib

import pytest

from embudo import config


@pytest.fixture
def wl(tmp_path, monkeypatch):
    # Redirige el almacenamiento a un directorio temporal y recarga el módulo.
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))
    from embudo import watchlist
    importlib.reload(watchlist)
    return watchlist


def test_empty_by_default(wl):
    assert wl.load() == []


def test_add_and_persist(wl):
    wl.add("nvda")
    assert wl.load() == ["NVDA"]  # normaliza a mayúsculas


def test_no_duplicates(wl):
    wl.add("AAPL")
    wl.add("aapl")
    assert wl.load() == ["AAPL"]


def test_remove(wl):
    wl.add("AAPL")
    wl.add("MSFT")
    wl.remove("AAPL")
    assert wl.load() == ["MSFT"]


def test_order_preserved(wl):
    for t in ["TSLA", "AMZN", "META"]:
        wl.add(t)
    assert wl.load() == ["TSLA", "AMZN", "META"]
