"""Detector de régimen de mercado (contexto top-down).

Antes de juzgar un valor, juzga el mercado: una señal alcista en mercado
bajista no vale lo mismo. Devuelve un semáforo global y un multiplicador que
modula la confianza de las señales alcistas/bajistas.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .indicators import technical


@dataclass
class Regime:
    label: str            # "Alcista" | "Lateral" | "Bajista"
    color: str            # "green" | "orange" | "red"
    score: float          # [-1, +1]
    detail: str

    def bias_multiplier(self, signal_score: float) -> float:
        """Atenúa señales que reman contra el régimen, premia las alineadas.

        Una compra en mercado alcista mantiene su fuerza; en mercado bajista se
        descuenta. Nunca anula la señal, solo la pondera (rango ~0.6..1.0).
        """
        aligned = signal_score * self.score >= 0
        strength = abs(self.score)
        if aligned:
            return 1.0
        return max(0.6, 1.0 - 0.4 * strength)


def detect(index_df: pd.DataFrame) -> Regime:
    """Determina el régimen a partir del histórico de un índice (p.ej. ^GSPC)."""
    if index_df is None or index_df.empty or len(index_df) < technical.config.SMA_SLOW:
        return Regime("Desconocido", "orange", 0.0, "Datos de índice insuficientes.")

    enriched = technical.enrich(index_df)
    close = float(enriched["Close"].iloc[-1])
    sma_slow = enriched["sma_slow"].iloc[-1]
    sma_fast = enriched["sma_fast"].iloc[-1]
    adx = enriched["adx"].iloc[-1]

    if pd.isna(sma_slow) or pd.isna(sma_fast):
        return Regime("Desconocido", "orange", 0.0, "Medias del índice no disponibles.")

    above_slow = close > sma_slow
    fast_above_slow = sma_fast > sma_slow
    trending = (not pd.isna(adx)) and adx >= 20

    if above_slow and fast_above_slow:
        score = 0.8 if trending else 0.5
        return Regime("Alcista", "green", score, "Índice sobre la media de 200 con estructura alcista.")
    if (not above_slow) and (not fast_above_slow):
        score = -0.8 if trending else -0.5
        return Regime("Bajista", "red", score, "Índice bajo la media de 200 con estructura bajista.")
    return Regime("Lateral", "orange", 0.0, "Señales mixtas: mercado sin dirección clara.")
