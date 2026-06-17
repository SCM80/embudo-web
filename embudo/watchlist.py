"""Watchlist de seguimiento "forward" (JSON local, sin servicios externos).

Al fijar una acción guarda su **precio y fecha de fijación** y **a qué estrategia
atendía**, para poder ver luego su **evolución** desde que la fijaste. Compatible
hacia atrás: si el fichero antiguo era una lista de tickers, se migra solo.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from . import config

_PATH = Path(config.CACHE_DIR) / "watchlist.json"


def _normalize(ticker: str) -> str:
    return ticker.strip().upper()


def _to_entry(item) -> dict:
    """Normaliza un elemento a {ticker, pin_price, pin_date, strategy}."""
    if isinstance(item, str):                       # formato antiguo: solo ticker
        return {"ticker": _normalize(item), "pin_price": None, "pin_date": None, "strategy": None}
    if isinstance(item, dict) and item.get("ticker"):
        return {
            "ticker": _normalize(str(item["ticker"])),
            "pin_price": item.get("pin_price"),
            "pin_date": item.get("pin_date"),
            "strategy": item.get("strategy"),
        }
    return {"ticker": "", "pin_price": None, "pin_date": None, "strategy": None}


def entries() -> list[dict]:
    """Lista de objetos de seguimiento (con precio/fecha/estrategia de fijación)."""
    try:
        if _PATH.exists():
            data = json.loads(_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                out = [_to_entry(x) for x in data]
                return [e for e in out if e["ticker"]]
    except Exception:
        pass
    return []


def tickers() -> list[str]:
    """Solo los tickers (para el escáner y demás usos)."""
    return [e["ticker"] for e in entries()]


# Compatibilidad: load() devuelve la lista de tickers (como antes).
def load() -> list[str]:
    return tickers()


def _save(items: list[dict]) -> None:
    try:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        # Únicos por ticker, preservando orden de inserción.
        seen: dict[str, dict] = {}
        for e in items:
            t = _normalize(e.get("ticker", ""))
            if t and t not in seen:
                seen[t] = {**e, "ticker": t}
        _PATH.write_text(json.dumps(list(seen.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def add(ticker: str, price: float | None = None, strategy: str | None = None) -> list[dict]:
    """Fija un valor guardando precio y estrategia (si se aportan) y la fecha de hoy."""
    items = entries()
    nt = _normalize(ticker)
    if nt and nt not in [e["ticker"] for e in items]:
        items.append({"ticker": nt, "pin_price": price,
                      "pin_date": date.today().isoformat(), "strategy": strategy})
        _save(items)
    return items


def set_price(ticker: str, price: float, strategy: str | None = None) -> None:
    """Fija/actualiza el precio de fijación de un valor ya en la lista (migrados)."""
    items = entries()
    nt = _normalize(ticker)
    for e in items:
        if e["ticker"] == nt:
            e["pin_price"] = price
            if not e.get("pin_date"):
                e["pin_date"] = date.today().isoformat()
            if strategy and not e.get("strategy"):
                e["strategy"] = strategy
    _save(items)


def remove(ticker: str) -> list[dict]:
    items = [e for e in entries() if e["ticker"] != _normalize(ticker)]
    _save(items)
    return items
