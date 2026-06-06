"""Catálogo de tickers conocidos para autocompletar (IBEX + EEUU).

Se usa para sugerir tickers según el usuario escribe en la watchlist. Es la
unión de los universos soportados; offline y sin red.
"""
from __future__ import annotations

from .universe import IBEX35, US_LARGE

# Nombres legibles de los valores del IBEX (los de EEUU se muestran por ticker).
IBEX_NAMES = {
    "ITX.MC": "Inditex", "SAN.MC": "Santander", "IBE.MC": "Iberdrola",
    "BBVA.MC": "BBVA", "TEF.MC": "Telefónica", "REP.MC": "Repsol",
    "AMS.MC": "Amadeus", "FER.MC": "Ferrovial", "AENA.MC": "Aena",
    "CABK.MC": "CaixaBank", "ELE.MC": "Endesa", "NTGY.MC": "Naturgy",
    "RED.MC": "Redeia", "ACS.MC": "ACS", "GRF.MC": "Grifols", "MAP.MC": "Mapfre",
    "CLNX.MC": "Cellnex", "ANA.MC": "Acciona", "ENG.MC": "Enagás",
    "MTS.MC": "ArcelorMittal", "IAG.MC": "IAG", "BKT.MC": "Bankinter",
    "COL.MC": "Colonial", "MEL.MC": "Meliá", "SAB.MC": "Banco Sabadell",
    "SLR.MC": "Solaria", "FDR.MC": "Fluidra", "LOG.MC": "Logista",
    "ROVI.MC": "Rovi", "ACX.MC": "Acerinox", "IDR.MC": "Indra",
    "PUIG.MC": "Puig", "UNI.MC": "Unicaja", "CIE.MC": "CIE Automotive",
    "RVI.MC": "Línea Directa",
}

# Lista ordenada de todos los tickers disponibles.
ALL_TICKERS: list[str] = sorted(set(IBEX35) | set(US_LARGE))


def label(ticker: str) -> str:
    """Texto para mostrar en el desplegable: 'SAB.MC — Banco Sabadell'."""
    name = IBEX_NAMES.get(ticker)
    return f"{ticker} — {name}" if name else ticker


def suggestions() -> list[str]:
    """Tickers ordenados poniendo el IBEX primero (mercado del usuario)."""
    ibex = sorted(IBEX35)
    us = sorted(set(US_LARGE) - set(IBEX35))
    return ibex + us
