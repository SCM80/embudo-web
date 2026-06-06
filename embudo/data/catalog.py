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

# Nombres de las empresas de EEUU más reconocibles (Mag7, Dow30 y top Nasdaq).
US_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet (A)", "GOOG": "Alphabet (C)",
    "AMZN": "Amazon", "NVDA": "NVIDIA", "META": "Meta", "TSLA": "Tesla", "AVGO": "Broadcom",
    "PEP": "PepsiCo", "COST": "Costco", "ADBE": "Adobe", "CSCO": "Cisco", "NFLX": "Netflix",
    "AMD": "AMD", "TMUS": "T-Mobile", "INTC": "Intel", "CMCSA": "Comcast", "QCOM": "Qualcomm",
    "INTU": "Intuit", "AMGN": "Amgen", "TXN": "Texas Instruments", "HON": "Honeywell",
    "AMAT": "Applied Materials", "BKNG": "Booking", "ISRG": "Intuitive Surgical",
    "VRTX": "Vertex", "ADP": "ADP", "REGN": "Regeneron", "GILD": "Gilead", "MU": "Micron",
    "LRCX": "Lam Research", "PANW": "Palo Alto Networks", "SBUX": "Starbucks",
    "MDLZ": "Mondelez", "ADI": "Analog Devices", "PYPL": "PayPal", "KLAC": "KLA",
    "SNPS": "Synopsys", "CDNS": "Cadence", "MAR": "Marriott", "ASML": "ASML", "ABNB": "Airbnb",
    "CRWD": "CrowdStrike", "ORLY": "O'Reilly", "NXPI": "NXP", "MNST": "Monster",
    "FTNT": "Fortinet", "ADSK": "Autodesk", "MRVL": "Marvell", "LULU": "Lululemon",
    "PDD": "PDD", "ARM": "Arm", "TER": "Teradyne", "DDOG": "Datadog", "TTD": "Trade Desk",
    "TEAM": "Atlassian", "ZS": "Zscaler", "MRNA": "Moderna", "DASH": "DoorDash",
    "SMCI": "Super Micro", "LIN": "Linde", "GEHC": "GE HealthCare", "CEG": "Constellation",
    # Dow 30 adicionales
    "JNJ": "Johnson & Johnson", "V": "Visa", "WMT": "Walmart", "JPM": "JPMorgan",
    "PG": "Procter & Gamble", "UNH": "UnitedHealth", "HD": "Home Depot", "DIS": "Disney",
    "KO": "Coca-Cola", "MRK": "Merck", "VZ": "Verizon", "MCD": "McDonald's", "BA": "Boeing",
    "CVX": "Chevron", "IBM": "IBM", "NKE": "Nike", "CAT": "Caterpillar", "GS": "Goldman Sachs",
    "AXP": "American Express", "TRV": "Travelers", "MMM": "3M", "CRM": "Salesforce",
    "DOW": "Dow", "WBA": "Walgreens",
}

NAMES = {**IBEX_NAMES, **US_NAMES}

# Lista ordenada de todos los tickers disponibles.
ALL_TICKERS: list[str] = sorted(set(IBEX35) | set(US_LARGE))


def label(ticker: str) -> str:
    """Texto para mostrar en el desplegable: 'SAB.MC — Banco Sabadell'."""
    name = NAMES.get(ticker)
    return f"{ticker} — {name}" if name else ticker


def suggestions() -> list[str]:
    """Tickers ordenados poniendo el IBEX primero (mercado del usuario)."""
    ibex = sorted(IBEX35)
    us = sorted(set(US_LARGE) - set(IBEX35))
    return ibex + us
