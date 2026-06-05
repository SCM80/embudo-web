"""Motor de consenso: combina técnico + analistas + sentimiento.

Decisión de diseño clave: NO escondemos el desacuerdo. El consenso devuelve el
score combinado PERO también el de cada dimensión y una "confianza" que mide el
ACUERDO entre fuentes. Si técnico y cualitativo se contradicen, la confianza
baja y se avisa explícitamente — ahí es donde el humano debe pensar.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .. import config
from ..profiles import StrategyProfile
from ..qualitative import analysts, sentiment
from ..qualitative.analysts import AnalystView
from ..qualitative.sentiment import SentimentView
from ..regime import Regime
from ..signals import horizons
from ..signals.base import Signal, SignalGroup


@dataclass
class Consensus:
    score: float                  # [-1, +1] combinado y modulado por régimen
    label: str                    # etiqueta legible
    confidence: float             # [0, 1] acuerdo entre fuentes
    dimension_scores: dict[str, float] = field(default_factory=dict)
    technical: SignalGroup | None = None
    analyst: AnalystView | None = None
    sentiment: SentimentView | None = None
    conflict: str | None = None   # aviso si las dimensiones se contradicen
    regime_note: str | None = None

    @property
    def direction(self) -> int:
        return 1 if self.score > 0 else -1 if self.score < 0 else 0


def _confidence(dim_scores: dict[str, float], weights: dict[str, float]) -> tuple[float, str | None]:
    """Confianza = 1 - dispersión ponderada entre dimensiones activas.

    Si las dimensiones apuntan al mismo sitio -> alta confianza.
    Si se contradicen (signos opuestos con peso real) -> baja + aviso.
    """
    active = {k: v for k, v in dim_scores.items() if weights.get(k, 0) > 0}
    if not active:
        return 0.0, None
    mean = sum(active.values()) / len(active)
    spread = sum(abs(v - mean) for v in active.values()) / len(active)
    confidence = max(0.0, 1.0 - spread)

    signs = {k: (1 if v > 0.1 else -1 if v < -0.1 else 0) for k, v in active.items()}
    pos = [k for k, s in signs.items() if s > 0]
    neg = [k for k, s in signs.items() if s < 0]
    conflict = None
    if pos and neg:
        conflict = f"⚠️ Desacuerdo: {', '.join(pos)} apunta(n) a compra y {', '.join(neg)} a venta."
        confidence *= 0.7
    return round(confidence, 2), conflict


def evaluate(
    df: pd.DataFrame,
    profile: StrategyProfile,
    analyst_view: AnalystView | None = None,
    sentiment_view: SentimentView | None = None,
    regime: Regime | None = None,
) -> Consensus:
    """Calcula el consenso para un valor dado un perfil de estrategia."""
    weights = profile.weights

    tech_group = horizons.evaluate(df, profile.horizon)
    tech_score = tech_group.score

    analyst_view = analyst_view or analysts.from_mean(None)
    sentiment_view = sentiment_view or sentiment.analyze([])
    analyst_sig = analysts.to_signal(analyst_view)
    sentiment_sig = sentiment.to_signal(sentiment_view)

    dim_scores = {
        "tecnico": tech_score,
        "analistas": analyst_view.score if analyst_sig.weight > 0 else 0.0,
        "sentimiento": sentiment_view.score if sentiment_sig.weight > 0 else 0.0,
    }

    # Solo cuentan las dimensiones con datos reales (degradación elegante).
    eff_weights = dict(weights)
    if analyst_sig.weight == 0:
        eff_weights["analistas"] = 0.0
    if sentiment_sig.weight == 0:
        eff_weights["sentimiento"] = 0.0
    total_w = sum(eff_weights.values()) or 1.0

    combined = sum(dim_scores[k] * eff_weights[k] for k in dim_scores) / total_w

    regime_note = None
    if regime is not None:
        mult = regime.bias_multiplier(combined)
        if mult < 1.0:
            regime_note = f"Régimen {regime.label}: señal atenuada (×{mult:.2f}) por remar contra el mercado."
        combined *= mult

    combined = max(-1.0, min(1.0, combined))
    confidence, conflict = _confidence(dim_scores, eff_weights)

    return Consensus(
        score=round(combined, 3),
        label=config.score_to_label(combined),
        confidence=confidence,
        dimension_scores={k: round(v, 3) for k, v in dim_scores.items()},
        technical=tech_group,
        analyst=analyst_view,
        sentiment=sentiment_view,
        conflict=conflict,
        regime_note=regime_note,
    )
