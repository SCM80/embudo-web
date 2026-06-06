"""Acceso a datos de Yahoo Finance (gratis, sin API key) con caché y fallback.

yfinance es no oficial y aplica rate-limit al escanear universos. Mitigamos con:
- Caché local en parquet (TTL configurable) para no repetir descargas.
- Fallback a Stooq (también gratis, sin key) si Yahoo falla con datos diarios.

Toda la E/S de red está aislada aquí; el resto del paquete trabaja con
DataFrames OHLCV y no sabe de dónde vienen.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd

from .. import config

_CACHE = Path(config.CACHE_DIR)


def _cache_path(key: str) -> Path:
    safe = "".join(c if c.isalnum() else "_" for c in key)
    return _CACHE / f"{safe}.parquet"


def _read_cache(key: str) -> pd.DataFrame | None:
    path = _cache_path(key)
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > config.CACHE_TTL_SECONDS:
        return None
    try:
        return pd.read_parquet(path)
    except Exception:
        return None


def _write_cache(key: str, df: pd.DataFrame) -> None:
    try:
        _CACHE.mkdir(parents=True, exist_ok=True)
        df.to_parquet(_cache_path(key))
    except Exception:
        pass  # la caché es best-effort, nunca debe romper el flujo


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Garantiza columnas OHLCV estándar y orden temporal."""
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    cols = {c.title(): c for c in df.columns}
    rename = {}
    for std in ("Open", "High", "Low", "Close", "Volume"):
        if std in df.columns:
            continue
        if std in cols:
            rename[cols[std]] = std
    df = df.rename(columns=rename)
    keep = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]
    df = df[keep].dropna(how="all").sort_index()
    return df


def get_prices(ticker: str, period: str = "2y", interval: str = "1d", use_cache: bool = True) -> pd.DataFrame:
    """Descarga OHLCV. Modo demo si está activo; si no, Yahoo y, para diario, Stooq."""
    if config.DEMO_MODE:
        from . import demo
        return _normalize(demo.demo_prices(ticker, period, interval))

    key = f"{ticker}_{period}_{interval}"
    if use_cache:
        cached = _read_cache(key)
        if cached is not None:
            return cached

    df = _from_yahoo(ticker, period, interval)
    if (df is None or df.empty) and interval == "1d":
        df = _from_stooq(ticker)

    df = _normalize(df if df is not None else pd.DataFrame())
    if not df.empty:
        _write_cache(key, df)
    return df


def get_prices_batch(tickers: list[str], period: str = "2y", interval: str = "1d") -> dict[str, pd.DataFrame]:
    """Descarga OHLCV de MUCHOS tickers de una vez (rápido, menos rate-limit).

    Devuelve {ticker: DataFrame}. Cachea cada uno para que abrir su ficha sea
    instantáneo. Los tickers que fallen simplemente no aparecen en el resultado.
    """
    out: dict[str, pd.DataFrame] = {}
    tickers = list(tickers)
    if config.DEMO_MODE:
        from . import demo
        return {t: _normalize(demo.demo_prices(t, period, interval)) for t in tickers}

    try:
        import yfinance as yf
        data = yf.download(tickers, period=period, interval=interval, auto_adjust=True,
                           progress=False, threads=True, group_by="ticker")
    except Exception:
        data = None
    if data is None or data.empty:
        return out

    for t in tickers:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if t not in data.columns.get_level_values(0):
                    continue
                df = data[t]
            else:
                df = data  # caso de un solo ticker
            df = _normalize(df)
            if not df.empty:
                out[t] = df
                _write_cache(f"{t}_{period}_{interval}", df)
        except Exception:
            continue
    return out


def _from_yahoo(ticker: str, period: str, interval: str) -> pd.DataFrame | None:
    try:
        import yfinance as yf

        return yf.download(
            ticker, period=period, interval=interval,
            auto_adjust=True, progress=False, threads=False,
        )
    except Exception:
        return None


def _from_stooq(ticker: str) -> pd.DataFrame | None:
    """Fallback gratuito y sin key (datos diarios) vía CSV de Stooq."""
    try:
        import io

        import requests

        symbol = ticker.lower()
        if "." not in symbol and "-" not in symbol:
            symbol = f"{symbol}.us"  # convención Stooq para valores USA
        url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200 or not resp.text.startswith("Date"):
            return None
        df = pd.read_csv(io.StringIO(resp.text), parse_dates=["Date"]).set_index("Date")
        return df
    except Exception:
        return None


def get_fundamentals(ticker: str) -> dict:
    """Datos cualitativos y fundamentales de Yahoo: analistas, noticias, calidad/valor.

    Todos los campos pueden venir vacíos según el activo; los consumidores deben
    degradar con elegancia (peso 0) cuando falten.
    """
    out = {
        "recommendation_mean": None, "num_analysts": 0, "headlines": [], "name": ticker,
        # Fundamentales (Buffett: calidad/valor)
        "roe": None, "debt_to_equity": None, "profit_margins": None,
        "trailing_pe": None, "forward_pe": None,
        "revenue_growth": None, "earnings_growth": None,
        # KPIs de cabecera
        "market_cap": None, "fifty_two_high": None, "fifty_two_low": None, "beta": None,
    }
    if config.DEMO_MODE:
        from . import demo
        return demo.demo_fundamentals(ticker)
    try:
        import yfinance as yf

        tk = yf.Ticker(ticker)
        try:
            info = tk.get_info()
        except Exception:
            info = getattr(tk, "info", {}) or {}
        out["recommendation_mean"] = info.get("recommendationMean")
        out["num_analysts"] = info.get("numberOfAnalystOpinions", 0) or 0
        out["name"] = info.get("shortName") or info.get("longName") or ticker
        # Fundamentales
        out["roe"] = info.get("returnOnEquity")
        out["debt_to_equity"] = info.get("debtToEquity")
        out["profit_margins"] = info.get("profitMargins")
        out["trailing_pe"] = info.get("trailingPE")
        out["forward_pe"] = info.get("forwardPE")
        out["revenue_growth"] = info.get("revenueGrowth")
        out["earnings_growth"] = info.get("earningsGrowth")
        # KPIs
        out["market_cap"] = info.get("marketCap")
        out["fifty_two_high"] = info.get("fiftyTwoWeekHigh")
        out["fifty_two_low"] = info.get("fiftyTwoWeekLow")
        out["beta"] = info.get("beta")

        try:
            news = tk.news or []
            heads = []
            for item in news[:15]:
                title = item.get("title") or (item.get("content", {}) or {}).get("title")
                if title:
                    heads.append(title)
            out["headlines"] = heads
        except Exception:
            pass
    except Exception:
        pass
    return out
