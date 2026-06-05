"""Watchlist propia persistente (JSON local, sin servicios externos).

Permite al usuario guardar sus tickers favoritos y usarlos como universo en el
screener. Se guarda en un fichero JSON local; la E/S es best-effort y nunca
rompe el flujo de la app.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config

_PATH = Path(config.CACHE_DIR) / "watchlist.json"


def _normalize(ticker: str) -> str:
    return ticker.strip().upper()


def load() -> list[str]:
    try:
        if _PATH.exists():
            data = json.loads(_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [str(t) for t in data]
    except Exception:
        pass
    return []


def save(tickers: list[str]) -> None:
    try:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        # Únicos, en mayúsculas, preservando orden de inserción.
        seen: dict[str, None] = {}
        for t in tickers:
            nt = _normalize(t)
            if nt:
                seen.setdefault(nt, None)
        _PATH.write_text(json.dumps(list(seen.keys()), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def add(ticker: str) -> list[str]:
    tickers = load()
    nt = _normalize(ticker)
    if nt and nt not in tickers:
        tickers.append(nt)
        save(tickers)
    return tickers


def remove(ticker: str) -> list[str]:
    tickers = [t for t in load() if t != _normalize(ticker)]
    save(tickers)
    return tickers
