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
    """Descarga OHLCV. Intenta Yahoo y, para datos diarios, cae a Stooq si falla."""
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
    """Datos cualitativos de Yahoo: media de recomendación de analistas y noticias."""
    out = {"recommendation_mean": None, "num_analysts": 0, "headlines": [], "name": ticker}
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
