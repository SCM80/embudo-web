"""Termómetro de mercado: contexto global (NO es una predicción).

Combina, de forma honesta y con datos gratuitos:
- VIX ("índice del miedo"): calma / normal / miedo / pánico.
- Régimen del S&P 500 (precio vs media de 200, estructura).
- Sentimiento de noticias macro (VADER sobre titulares de mercado).
- Amplitud (% de candidatos alcistas del último escaneo), si se proporciona.

El objetivo es dar el "clima" para decidir si pisar el acelerador o ser cauto,
sin prometer adivinar el futuro.
"""
from __future__ import annotations

from dataclasses import dataclass

from .data import yahoo
from .qualitative import sentiment
from .qualitative.sentiment import SentimentView
from .regime import Regime, detect


@dataclass
class MarketContext:
    vix: float | None
    vix_change: float | None
    vix_label: str
    vix_color: str
    regime: Regime | None
    news: SentimentView | None
    breadth: float | None          # fracción [0,1] de candidatos alcistas
    clima_label: str               # "Favorable" | "Mixto" | "Adverso"
    clima_color: str               # green | orange | red
    detail: str


def vix_reading(v: float | None) -> tuple[str, str]:
    """Devuelve (etiqueta, color) según el nivel del VIX."""
    if v is None:
        return "—", "orange"
    if v < 15:
        return "Calma", "green"
    if v < 25:
        return "Normal", "orange"
    if v < 30:
        return "Miedo", "red"
    return "Pánico", "darkred"


def _vix_score(v: float | None) -> float:
    """VIX a [-1, +1]: calma = positivo, pánico = muy negativo."""
    if v is None:
        return 0.0
    if v < 15:
        return 0.5
    if v < 25:
        return 0.0
    if v < 30:
        return -0.5
    return -1.0


def market_context(breadth: float | None = None) -> MarketContext:
    # VIX (último cierre y variación).
    vix = vix_change = None
    try:
        vdf = yahoo.get_prices("^VIX", period="1mo", interval="1d")
        if vdf is not None and not vdf.empty:
            vix = round(float(vdf["Close"].iloc[-1]), 2)
            if len(vdf) > 1:
                prev = float(vdf["Close"].iloc[-2])
                vix_change = round((vix - prev) / prev * 100, 1) if prev else None
    except Exception:
        pass
    vix_label, vix_color = vix_reading(vix)

    # Régimen del S&P 500.
    regime = None
    try:
        idx = yahoo.get_prices("^GSPC", period="2y", interval="1d")
        if idx is not None and not idx.empty:
            regime = detect(idx)
    except Exception:
        pass

    # Sentimiento de noticias macro (titulares de mercado vía SPY).
    news = None
    try:
        fund = yahoo.get_fundamentals("SPY")
        news = sentiment.analyze(fund.get("headlines", []))
    except Exception:
        pass

    # Clima = combinación ponderada de lo disponible (degradación elegante).
    parts, weights = [], []
    if regime is not None:
        parts.append(regime.score); weights.append(0.5)
    parts.append(_vix_score(vix)); weights.append(0.3)
    if news is not None and news.n > 0:
        parts.append(news.score); weights.append(0.2)
    clima = sum(p * w for p, w in zip(parts, weights)) / (sum(weights) or 1.0)
    if breadth is not None:
        clima = clima * 0.8 + (breadth * 2 - 1) * 0.2   # amplitud ajusta un poco

    if clima >= 0.25:
        clima_label, clima_color = "Favorable", "green"
    elif clima <= -0.25:
        clima_label, clima_color = "Adverso", "red"
    else:
        clima_label, clima_color = "Mixto", "orange"

    bits = [f"VIX {vix} ({vix_label})" if vix is not None else "VIX n/d"]
    if regime is not None:
        bits.append(f"S&P 500 {regime.label}")
    if news is not None and news.n > 0:
        bits.append(f"noticias {'+' if news.score >= 0 else ''}{news.score:.2f}")
    detail = " · ".join(bits)

    return MarketContext(vix, vix_change, vix_label, vix_color, regime, news,
                         breadth, clima_label, clima_color, detail)
