"""Sentimiento de titulares con VADER (local, sin API, gratis).

VADER es un analizador basado en léxico orientado a textos cortos. Suficiente
para titulares financieros como refuerzo cualitativo. Si la librería no está
instalada o no hay titulares, degrada con peso 0 (no contamina el consenso).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..signals.base import Signal

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    _ANALYZER: SentimentIntensityAnalyzer | None = SentimentIntensityAnalyzer()
except Exception:  # pragma: no cover - entorno sin la dependencia
    _ANALYZER = None


@dataclass
class SentimentView:
    score: float                 # [-1, +1] (compound medio)
    n: int                       # nº de titulares analizados
    headlines: list[tuple[str, float]] = field(default_factory=list)
    detail: str = ""


def analyze(headlines: list[str]) -> SentimentView:
    headlines = [h for h in (headlines or []) if h and h.strip()]
    if _ANALYZER is None:
        return SentimentView(0.0, 0, [], "VADER no disponible (instala vaderSentiment).")
    if not headlines:
        return SentimentView(0.0, 0, [], "Sin titulares recientes.")

    scored = [(h, _ANALYZER.polarity_scores(h)["compound"]) for h in headlines]
    avg = sum(s for _, s in scored) / len(scored)
    sentido = "positivo" if avg > 0.05 else "negativo" if avg < -0.05 else "neutro"
    return SentimentView(
        score=max(-1.0, min(1.0, avg)),
        n=len(scored),
        headlines=scored,
        detail=f"Sentimiento de noticias {sentido} ({len(scored)} titulares, compound {avg:+.2f}).",
    )


def to_signal(view: SentimentView) -> Signal:
    weight = 0.0 if view.n == 0 else min(1.0, 0.3 + view.n / 20.0)
    return Signal("Sentimiento", view.score, weight, view.detail)
