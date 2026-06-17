"""Normaliza el consenso de analistas que Yahoo entrega gratis.

Yahoo expone recommendationMean (1=Strong Buy ... 5=Strong Sell). Lo
convertimos a un score [-1, +1] coherente con el resto del sistema.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..signals.base import Signal


@dataclass
class AnalystView:
    score: float          # [-1, +1] (positivo = compra)
    mean: float | None    # recommendationMean original (1..5), None si no hay
    n: int                # nº de analistas
    detail: str


def from_mean(mean: float | None, n: int = 0) -> AnalystView:
    """Convierte recommendationMean (1..5) a score [-1, +1].

    1 (Strong Buy) -> +1 ; 3 (Hold) -> 0 ; 5 (Strong Sell) -> -1.
    """
    if mean is None or mean <= 0:
        return AnalystView(0.0, None, n, "Sin consenso de analistas disponible.")
    score = (3.0 - float(mean)) / 2.0
    score = max(-1.0, min(1.0, score))
    sentido = "compra" if score > 0.15 else "venta" if score < -0.15 else "mantener"
    return AnalystView(score, float(mean), n, f"Consenso de analistas: {sentido} (media {mean:.2f}/5, {n} analistas).")


def to_signal(view: AnalystView) -> Signal:
    # Sin analistas: peso 0 para que no contamine el consenso (degradación elegante).
    weight = 0.0 if view.mean is None else min(1.5, 0.5 + (view.n or 0) / 20.0)
    return Signal("Analistas", view.score, weight, view.detail)
