"""Validación del score: ¿de verdad predice retornos? (evidencia, no intuición).

Recorre el histórico de un universo, calcula el score TÉCNICO objetivo en cada
barra y mide el retorno a futuro. Agrupa por etiqueta (Compra fuerte … Venta
fuerte) y comprueba si los scores altos rinden más que los bajos. Si no hay
relación monótona, el sistema no discrimina y hay que revisarlo.

⚠️ LIMITACIÓN HONESTA: solo se valida la parte TÉCNICA del score (precio/volumen),
que sí es "point-in-time". Los fundamentales/analistas/noticias de Yahoo son del
momento actual (no históricos), así que incluirlos aquí daría sesgo de look-ahead.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config
from .indicators import technical
from .signals import horizons
from .signals.horizons import Horizon


@dataclass
class Bucket:
    label: str
    n: int
    avg_return: float      # retorno medio a futuro (%)
    win_rate: float        # fracción con retorno > 0


@dataclass
class ValidationResult:
    horizon_bars: int
    n_obs: int
    correlation: float                 # corr(score, retorno futuro)
    buckets: list[Bucket] = field(default_factory=list)
    monotonic: bool = False
    verdict: str = ""


def validate(prices: dict[str, pd.DataFrame], horizon_bars: int = 10,
             step: int = 10, warmup: int = 200) -> ValidationResult:
    scores: list[float] = []
    rets: list[float] = []

    for df in prices.values():
        if df is None or len(df) < warmup + horizon_bars + 5:
            continue
        enriched = technical.enrich(df)
        close = enriched["Close"].to_numpy()
        for i in range(warmup, len(enriched) - horizon_bars, step):
            score = horizons.evaluate(enriched.iloc[: i + 1], Horizon.LARGO).score
            entry = close[i]
            if entry > 0:
                scores.append(score)
                rets.append((close[i + horizon_bars] - entry) / entry)

    if len(scores) < 30:
        return ValidationResult(horizon_bars, len(scores), 0.0, [], False,
                                "Datos insuficientes para validar.")

    s = np.array(scores)
    r = np.array(rets)
    corr = float(np.corrcoef(s, r)[0, 1]) if s.std() > 0 else 0.0

    buckets: list[Bucket] = []
    for lo, hi, label in [(0.5, 1.01, "Compra fuerte"), (0.15, 0.5, "Compra"),
                          (-0.15, 0.15, "Neutral"), (-0.5, -0.15, "Venta"),
                          (-1.01, -0.5, "Venta fuerte")]:
        mask = (s >= lo) & (s < hi)
        if mask.sum() == 0:
            continue
        rr = r[mask]
        buckets.append(Bucket(label, int(mask.sum()),
                              round(float(rr.mean()) * 100, 2),
                              round(float((rr > 0).mean()), 3)))

    # ¿Mayor score -> mayor retorno? (monotonía de la media por bucket, de Compra a Venta)
    order = ["Compra fuerte", "Compra", "Neutral", "Venta", "Venta fuerte"]
    by_label = {b.label: b.avg_return for b in buckets}
    seq = [by_label[l] for l in order if l in by_label]
    monotonic = len(seq) >= 2 and all(seq[i] >= seq[i + 1] for i in range(len(seq) - 1))

    if corr > 0.05 and monotonic:
        verdict = f"✅ El score SÍ discrimina: correlación {corr:+.2f} y a mejor etiqueta, mejor retorno."
    elif corr > 0.02:
        verdict = f"🟡 Señal débil pero positiva (correlación {corr:+.2f}). Margen de mejora."
    else:
        verdict = f"🔴 El score NO discrimina retornos (correlación {corr:+.2f}). Revisar criterios."

    return ValidationResult(horizon_bars, len(scores), round(corr, 3), buckets, monotonic, verdict)
