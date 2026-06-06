"""Decisor fácil: convierte el análisis en un veredicto claro de una frase.

Traduce el score del consenso (ya alineado con la dirección de la estrategia) en
un semáforo accionable: OPERAR / ESPERAR / EVITAR, con el profit esperado y el
riesgo resumidos. El objetivo es que el usuario decida de un vistazo.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Verdict:
    action: str        # "OPERAR" | "ESPERAR" | "EVITAR"
    color: str         # "green" | "orange" | "red"
    emoji: str
    phrase: str        # explicación en una frase


def decide(score: float, direction: int, profit_pct: float | None,
           rr: float | None, confidence: float) -> Verdict:
    """Veredicto claro a partir del score, la dirección de la estrategia y el plan.

    `strength` = fuerza de la señal A FAVOR de la estrategia: para estrategias
    largas es el propio score; para cortos, el score invertido (un score muy
    negativo es un gran corto).
    """
    strength = score if direction >= 0 else -score
    verb = "Comprar" if direction >= 0 else "Ponerse corto"
    conf = f"{confidence*100:.0f}%"
    prof = f"+{profit_pct:.1f}%" if profit_pct is not None else "—"
    rr_txt = f"{rr:.1f}" if rr is not None else "—"

    if strength >= 0.5:
        return Verdict("OPERAR", "green", "✅",
                       f"{verb.upper()}: señal fuerte a favor. Profit objetivo {prof} · "
                       f"R:R {rr_txt} · confianza {conf}.")
    if strength >= 0.15:
        return Verdict("OPERAR", "green", "🟢",
                       f"{verb} (moderado). Profit objetivo {prof} · R:R {rr_txt} · confianza {conf}.")
    if strength > -0.15:
        return Verdict("ESPERAR", "orange", "🟡",
                       f"Sin señal clara: mejor esperar. (Profit potencial {prof}, R:R {rr_txt}.)")
    return Verdict("EVITAR", "red", "🔴",
                   f"Señal en contra de la estrategia: evitar este valor ahora.")
