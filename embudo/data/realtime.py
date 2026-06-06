"""Cotización casi-real con clave gratuita opcional (Finnhub).

Los datos gratis de Yahoo van con ~15 min de retardo. Esta capa intenta dar la
cotización más fresca posible:
- Si hay `finnhub_key` y el ticker es de EEUU, usa Finnhub /quote (clave GRATIS).
- Si no, cae a yfinance fast_info / último cierre (con sello de hora).

Sin caché a propósito (queremos frescura). El histórico OHLCV sigue cacheado en
data.yahoo.get_prices.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Quote:
    price: float | None
    change_pct: float | None
    source: str
    asof: str            # hora local de la consulta (HH:MM:SS)
    delayed: bool        # True si el dato puede ir con retardo


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _is_us(ticker: str) -> bool:
    # Los tickers de Yahoo con sufijo (.MC, .DE...) no son de EEUU; Finnhub usa el símbolo plano.
    return "." not in ticker


def get_live_quote(ticker: str, finnhub_key: str | None = None) -> Quote:
    """Devuelve la cotización más fresca disponible para el ticker."""
    if finnhub_key and _is_us(ticker):
        q = _from_finnhub(ticker, finnhub_key)
        if q is not None:
            return q
    return _from_yahoo(ticker)


def _from_finnhub(ticker: str, key: str) -> Quote | None:
    try:
        import requests

        r = requests.get("https://finnhub.io/api/v1/quote",
                         params={"symbol": ticker, "token": key}, timeout=8)
        if r.status_code != 200:
            return None
        d = r.json()
        price, prev = d.get("c"), d.get("pc")
        if not price:
            return None
        change = ((price - prev) / prev * 100) if prev else d.get("dp")
        return Quote(round(float(price), 2),
                     round(float(change), 2) if change is not None else None,
                     "Finnhub (tiempo real)", _now(), delayed=False)
    except Exception:
        return None


def _from_yahoo(ticker: str) -> Quote:
    try:
        import yfinance as yf

        tk = yf.Ticker(ticker)
        price = prev = None
        try:
            fi = tk.fast_info
            price = fi.get("last_price") if hasattr(fi, "get") else getattr(fi, "last_price", None)
            prev = fi.get("previous_close") if hasattr(fi, "get") else getattr(fi, "previous_close", None)
        except Exception:
            pass
        if price is None:
            hist = tk.history(period="2d", interval="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
        change = ((price - prev) / prev * 100) if (price and prev) else None
        return Quote(round(float(price), 2) if price else None,
                     round(float(change), 2) if change is not None else None,
                     "Yahoo (retardo ~15 min)", _now(), delayed=True)
    except Exception:
        return Quote(None, None, "sin datos", _now(), delayed=True)
