"""Universos de valores para el screener.

Empezamos por universos pequeños (IBEX 35) para no saturar Yahoo y crecer hacia
índices grandes. El usuario también puede definir su propia watchlist.
"""
from __future__ import annotations

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
    "Dow Jones 30": DOW30,
}

# Índices de referencia para detectar el régimen de cada universo.
REGIME_INDEX = {
    "Magnificent 7 (rápido)": "^GSPC",
    "IBEX 35": "^IBEX",
    "EEUU (Nasdaq 100 + Dow 30)": "^NDX",
    "Dow Jones 30": "^DJI",
}
