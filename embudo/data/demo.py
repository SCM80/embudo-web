"""Modo demo: datos simulados realistas (sin red).

Permite usar toda la app sin conexión a fuentes externas: útil para probarla en
cualquier sitio, para demos y como degradación elegante cuando las fuentes
gratuitas fallan o limitan. Los datos son DETERMINISTAS por ticker (mismo
ticker -> mismos datos siempre), así la experiencia es coherente entre recargas.

⚠️ NO son datos reales de mercado. La cabecera y los nombres lo indican ("demo").
"""
from __future__ import annotations

import hashlib
from datetime import datetime

import numpy as np
import pandas as pd


def _rng(ticker: str, salt: int = 0) -> np.random.Generator:
    h = hashlib.md5(f"{ticker}{salt}".encode()).hexdigest()[:8]
    return np.random.default_rng(int(h, 16))


def demo_prices(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    rng = _rng(ticker)
    n = 240 if interval != "1d" else 520
    freq = "15min" if interval not in ("1d",) else "B"
    drift = rng.uniform(-0.0006, 0.0013)        # unos suben, otros bajan
    vol = rng.uniform(0.010, 0.030)
    shock = rng.normal(drift, vol, n)
    base = rng.uniform(20, 300)
    close = base * np.exp(np.cumsum(shock))
    idx = pd.date_range(end=datetime.today(), periods=n, freq=freq)
    close = pd.Series(close, index=idx)
    openp = close.shift(1).fillna(close.iloc[0])
    hi_wick = rng.uniform(0.001, 0.02, n)
    lo_wick = rng.uniform(0.001, 0.02, n)
    high = np.maximum(openp, close) * (1 + hi_wick)
    low = np.minimum(openp, close) * (1 - lo_wick)
    volume = pd.Series(rng.uniform(8e5, 9e6, n).round(), index=idx)
    return pd.DataFrame({"Open": openp, "High": high, "Low": low, "Close": close, "Volume": volume})


def demo_fundamentals(ticker: str) -> dict:
    rng = _rng(ticker, salt=7)
    price = float(demo_prices(ticker)["Close"].iloc[-1])
    return {
        "recommendation_mean": round(float(rng.uniform(1.4, 3.6)), 2),
        "num_analysts": int(rng.integers(3, 35)),
        "headlines": [
            f"{ticker}: resultados {'mejores' if rng.random() > 0.5 else 'peores'} de lo esperado (demo)",
            f"Analistas revisan el precio objetivo de {ticker} (demo)",
        ],
        "name": f"{ticker} (demo)",
        "roe": round(float(rng.uniform(-0.05, 0.32)), 3),
        "debt_to_equity": round(float(rng.uniform(10, 220)), 1),
        "profit_margins": round(float(rng.uniform(-0.08, 0.30)), 3),
        "trailing_pe": round(float(rng.uniform(8, 45)), 1),
        "forward_pe": round(float(rng.uniform(8, 40)), 1),
        "revenue_growth": round(float(rng.uniform(-0.12, 0.28)), 3),
        "earnings_growth": round(float(rng.uniform(-0.15, 0.35)), 3),
        "trailing_eps": round(float(rng.uniform(1.0, 12.0)), 2),
        "book_value": round(float(rng.uniform(5.0, 60.0)), 2),
        "price_to_book": round(float(rng.uniform(0.6, 8.0)), 2),
        "current_ratio": round(float(rng.uniform(0.7, 3.5)), 2),
        "earnings_date": _demo_earnings(rng),
        "market_cap": float(rng.uniform(1e9, 2e12)),
        "fifty_two_high": round(price * float(rng.uniform(1.05, 1.4)), 2),
        "fifty_two_low": round(price * float(rng.uniform(0.6, 0.95)), 2),
        "beta": round(float(rng.uniform(0.6, 1.8)), 2),
    }


def _demo_earnings(rng) -> str:
    from datetime import date, timedelta
    # A veces resultados inminentes (para ver el aviso), a veces lejanos.
    days = int(rng.choice([3, 5, 8, 20, 45, 70]))
    return (date.today() + timedelta(days=days)).isoformat()


def demo_quote(ticker: str) -> tuple[float, float]:
    """Devuelve (precio, cambio %) simulado coherente con el histórico demo."""
    df = demo_prices(ticker)
    price = float(df["Close"].iloc[-1])
    prev = float(df["Close"].iloc[-2]) if len(df) > 1 else price
    change = (price - prev) / prev * 100 if prev else 0.0
    return round(price, 2), round(change, 2)
