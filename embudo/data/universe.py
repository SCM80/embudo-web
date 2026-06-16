"""Universos de valores para el screener.

Las listas se **actualizan solas** desde Wikipedia (componentes de cada índice)
con caché local; si no hay red o falla, se usan las listas estáticas de respaldo
que hay más abajo. Así el mercado se mantiene al día sin romperse nunca offline.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .. import config

# IBEX 35 (sufijo .MC = Bolsa de Madrid en Yahoo).
IBEX35 = [
    "ITX.MC", "SAN.MC", "IBE.MC", "BBVA.MC", "TEF.MC", "REP.MC", "AMS.MC",
    "FER.MC", "AENA.MC", "CABK.MC", "ELE.MC", "NTGY.MC", "RED.MC", "ACS.MC",
    "GRF.MC", "MAP.MC", "CLNX.MC", "ANA.MC", "ENG.MC", "MTS.MC", "IAG.MC",
    "BKT.MC", "COL.MC", "MEL.MC", "SAB.MC", "SLR.MC", "FDR.MC", "LOG.MC",
    "ROVI.MC", "ACX.MC", "IDR.MC", "PUIG.MC", "UNI.MC", "CIE.MC", "RVI.MC",
]

# Dow Jones 30 (universo USA manejable y líquido).
DOW30 = [
    "AAPL", "MSFT", "JNJ", "V", "WMT", "JPM", "PG", "UNH", "HD", "DIS",
    "KO", "MRK", "CSCO", "VZ", "INTC", "MCD", "BA", "CVX", "AMGN", "IBM",
    "NKE", "CAT", "GS", "AXP", "TRV", "HON", "MMM", "CRM", "DOW", "WBA",
]

# "Magnificent 7" para pruebas rápidas.
MAG7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

# Nasdaq 100 (tecnología y growth USA).
NASDAQ100 = [
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "AVGO", "PEP",
    "COST", "ADBE", "CSCO", "NFLX", "AMD", "TMUS", "INTC", "CMCSA", "QCOM", "INTU",
    "AMGN", "TXN", "HON", "AMAT", "BKNG", "ISRG", "VRTX", "ADP", "REGN", "GILD",
    "MU", "LRCX", "PANW", "SBUX", "MDLZ", "ADI", "PYPL", "KLAC", "SNPS", "CDNS",
    "MELI", "MAR", "ASML", "ABNB", "CRWD", "ORLY", "CTAS", "NXPI", "PCAR", "MNST",
    "WDAY", "FTNT", "PAYX", "ODP", "CPRT", "ROST", "DXCM", "KDP", "IDXX", "FAST",
    "EA", "VRSK", "EXC", "CSGP", "CCEP", "KHC", "BKR", "XEL", "CTSH", "DDOG",
    "ON", "ANSS", "TTD", "GEHC", "BIIB", "MRVL", "DLTR", "WBD", "CDW", "FANG",
    "TEAM", "ZS", "ADSK", "GFS", "ILMN", "MCHP", "LULU", "PDD", "ROP", "AEP",
    "CEG", "SIRI", "WBA", "TTWO", "MRNA", "DASH", "SMCI", "ARM", "LIN", "TER",
]

# Combinado EEUU (Nasdaq 100 + Dow 30, sin duplicados, preservando orden).
US_LARGE = list(dict.fromkeys(NASDAQ100 + DOW30))

UNIVERSES: dict[str, list[str]] = {
    "Magnificent 7 (rápido)": MAG7,
    "IBEX 35": IBEX35,
    "EEUU (Nasdaq 100 + Dow 30)": US_LARGE,
    "S&P 500": US_LARGE,            # contenido real vía descarga dinámica
    "Dow Jones 30": DOW30,
}

# Índices de referencia para detectar el régimen de cada universo.
REGIME_INDEX = {
    "Magnificent 7 (rápido)": "^GSPC",
    "IBEX 35": "^IBEX",
    "EEUU (Nasdaq 100 + Dow 30)": "^NDX",
    "S&P 500": "^GSPC",
    "Dow Jones 30": "^DJI",
}


# ----------------------- universos dinámicos (Wikipedia) -----------------------

_TTL = 7 * 24 * 3600  # refrescar las listas como mucho una vez por semana
_DIR = Path(config.CACHE_DIR) / "universes"

# clave -> (url de Wikipedia, columnas candidatas, normalizador, fallback estático)
_WIKI = "https://en.wikipedia.org/wiki/"
_SOURCES = {
    "ibex35":   (_WIKI + "IBEX_35", ("ticker", "symbol", "símbolo"), "ibex", IBEX35),
    "nasdaq100": (_WIKI + "Nasdaq-100", ("ticker", "symbol"), "us", NASDAQ100),
    "dow30":    (_WIKI + "Dow_Jones_Industrial_Average", ("symbol", "ticker"), "us", DOW30),
    "sp500":    (_WIKI + "List_of_S%26P_500_companies", ("symbol",), "us", US_LARGE),
}


def _norm(sym: str, kind: str) -> str:
    s = str(sym).strip().upper()
    if kind == "us":
        return s.replace(".", "-")          # BRK.B -> BRK-B (formato Yahoo)
    return s if s.endswith(".MC") else f"{s}.MC"


def _cache_read(key: str):
    p = _DIR / f"{key}.json"
    if not p.exists() or time.time() - p.stat().st_mtime > _TTL:
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cache_write(key: str, symbols: list[str]) -> None:
    try:
        _DIR.mkdir(parents=True, exist_ok=True)
        (_DIR / f"{key}.json").write_text(json.dumps(symbols), encoding="utf-8")
    except Exception:
        pass


def _fetch(key: str) -> list[str]:
    """Descarga los componentes desde Wikipedia. [] si falla (sin red, etc.)."""
    url, cols, kind, _ = _SOURCES[key]
    try:
        import pandas as pd
        for df in pd.read_html(url):
            low = {str(c).strip().lower(): c for c in df.columns}
            for cand in cols:
                if cand in low:
                    syms = [_norm(s, kind) for s in df[low[cand]].astype(str)
                            if s and str(s).lower() != "nan"]
                    if len(syms) >= 10:
                        return list(dict.fromkeys(syms))
    except Exception:
        pass
    return []


def _constituents(key: str) -> list[str]:
    """Componentes de un índice: caché fresca → descarga → caché vieja → fallback."""
    if config.DEMO_MODE:
        return _SOURCES[key][3]
    cached = _cache_read(key)
    if cached:
        return cached
    fetched = _fetch(key)
    if fetched:
        _cache_write(key, fetched)
        return fetched
    # Sin red: caché caducada si existe, o lista estática de respaldo.
    p = _DIR / f"{key}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _SOURCES[key][3]


def get_universe(name: str) -> list[str]:
    """Lista de tickers de un universo, dinámica y con fallback."""
    if name == "Magnificent 7 (rápido)":
        return MAG7
    if name == "IBEX 35":
        return _constituents("ibex35")
    if name == "Dow Jones 30":
        return _constituents("dow30")
    if name == "S&P 500":
        return _constituents("sp500")
    if name == "EEUU (Nasdaq 100 + Dow 30)":
        return list(dict.fromkeys(_constituents("nasdaq100") + _constituents("dow30")))
    return UNIVERSES.get(name, [])


def last_updated(name: str) -> str | None:
    """Fecha (YYYY-MM-DD) de la última actualización de las listas del universo."""
    keys = {"IBEX 35": ["ibex35"], "Dow Jones 30": ["dow30"], "S&P 500": ["sp500"],
            "EEUU (Nasdaq 100 + Dow 30)": ["nasdaq100", "dow30"]}.get(name, [])
    mtimes = [(_DIR / f"{k}.json").stat().st_mtime for k in keys if (_DIR / f"{k}.json").exists()]
    if not mtimes:
        return None
    from datetime import datetime
    return datetime.fromtimestamp(min(mtimes)).strftime("%Y-%m-%d")


def refresh_all() -> None:
    """Borra la caché de universos para forzar una descarga fresca."""
    try:
        for p in _DIR.glob("*.json"):
            p.unlink()
    except Exception:
        pass
