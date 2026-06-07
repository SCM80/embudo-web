"""Tipo de cambio para sizing correcto cuando el valor cotiza en otra moneda.

Los precios de EEUU están en USD pero el capital del usuario está en EUR. Para
que el tamaño de posición y el riesgo en euros sean exactos, convertimos el
riesgo por acción a EUR con el cambio USD→EUR.
"""
from __future__ import annotations

from .. import config


def usd_to_eur(default: float = 0.92) -> float:
    """EUR por 1 USD. En demo o si falla la red, usa un valor por defecto."""
    if config.DEMO_MODE:
        return default
    try:
        import yfinance as yf
        df = yf.download("EURUSD=X", period="5d", interval="1d",
                         progress=False, threads=False)
        if df is not None and not df.empty:
            eurusd = float(df["Close"].iloc[-1])  # USD por 1 EUR
            if eurusd > 0:
                return round(1.0 / eurusd, 4)
    except Exception:
        pass
    return default


def to_eur_rate(ticker: str) -> float:
    """Factor para pasar el precio del ticker a EUR (1.0 si ya cotiza en EUR)."""
    is_eur = "." in ticker and not ticker.upper().endswith(".US")
    return 1.0 if is_eur else usd_to_eur()
