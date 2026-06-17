"""Catálogo de tickers para autocompletar y BUSCAR por nombre.

Por defecto usa los componentes de los índices soportados (offline). Si hay red,
`load_full()` descarga el directorio completo de símbolos de NYSE+NASDAQ (gratis,
NASDAQ Trader) para poder buscar cualquier valor del mercado por nombre o ticker.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .. import config
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


# ---------------- Catálogo completo del mercado (NYSE+NASDAQ) ----------------

_CACHE = Path(config.CACHE_DIR) / "symbol_catalog.json"
_TTL = 30 * 24 * 3600  # se actualiza como mucho una vez al mes
_NASDAQ_FILES = [
    "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
]


def _fetch_full() -> dict[str, str]:
    """Descarga el directorio de símbolos NYSE+NASDAQ. {} si falla (sin red)."""
    out: dict[str, str] = {}
    try:
        import requests
        for url in _NASDAQ_FILES:
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                continue
            for line in r.text.splitlines()[1:]:
                parts = line.split("|")
                if len(parts) < 2 or parts[0] in ("", "Symbol", "ACT Symbol"):
                    continue
                if "File Creation Time" in line:
                    continue
                sym = parts[0].strip().upper().replace(".", "-")
                name = parts[1].strip()
                if sym and name:
                    out[sym] = name
    except Exception:
        return {}
    return out


def load_full() -> dict[str, str]:
    """Mapa ticker→nombre de TODO el mercado (cacheado). Fallback al catálogo base."""
    if config.DEMO_MODE:
        return dict(NAMES)
    try:
        if _CACHE.exists() and time.time() - _CACHE.stat().st_mtime < _TTL:
            data = json.loads(_CACHE.read_text(encoding="utf-8"))
            if data:
                return {**NAMES, **data}
    except Exception:
        pass
    fetched = _fetch_full()
    if fetched:
        try:
            _CACHE.parent.mkdir(parents=True, exist_ok=True)
            _CACHE.write_text(json.dumps(fetched), encoding="utf-8")
        except Exception:
            pass
        return {**NAMES, **fetched}
    return dict(NAMES)


def search(query: str, limit: int = 20) -> list[tuple[str, str]]:
    """Busca por ticker o nombre en todo el mercado. Devuelve [(ticker, nombre)]."""
    q = (query or "").strip().upper()
    if not q:
        return []
    catalog = load_full()
    starts, contains = [], []
    for sym, name in catalog.items():
        up_name = name.upper()
        if sym == q or up_name == q:
            starts.insert(0, (sym, name))
        elif sym.startswith(q) or up_name.startswith(q):
            starts.append((sym, name))
        elif q in sym or q in up_name:
            contains.append((sym, name))
        if len(starts) >= limit:
            break
    return (starts + contains)[:limit]
