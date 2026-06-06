"""Comprobación de conectividad a datos reales.

Permite a la app saber si puede obtener datos reales de mercado (Yahoo) o si
debe caer al modo demo. Útil para mostrar al usuario un estado claro
("🟢 datos reales" / "🔴 sin conexión").
"""
from __future__ import annotations


def check_connectivity(timeout: int = 8) -> bool:
    """True si se puede descargar al menos un dato real de Yahoo Finance."""
    try:
        import yfinance as yf

        df = yf.download("AAPL", period="5d", interval="1d",
                         progress=False, threads=False)
        return df is not None and not df.empty
    except Exception:
        return False
