"""Gestión de riesgo: ningún plan de entrada sin su salida.

Calcula stop (basado en ATR), tamaño de posición para arriesgar un % fijo del
capital y objetivo según un ratio beneficio/riesgo. El R:R decide si la
operación merece la pena, independientemente de lo buena que parezca la señal.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import config


@dataclass
class TradePlan:
    direction: int              # +1 largo, -1 corto
    entry: float
    stop: float
    target: float
    risk_per_share: float
    reward_per_share: float
    reward_risk: float
    shares: int
    capital_at_risk: float
    detail: str


def build_plan(
    entry: float,
    atr: float,
    direction: int,
    capital: float,
    risk_pct: float = config.DEFAULT_RISK_PER_TRADE,
    atr_mult: float = config.DEFAULT_ATR_STOP_MULT,
    reward_risk: float = config.DEFAULT_REWARD_RISK,
) -> TradePlan | None:
    """Construye un plan de trade. Devuelve None si los datos no son válidos."""
    if not entry or not atr or atr <= 0 or direction == 0:
        return None

    stop_distance = atr_mult * atr
    if direction > 0:
        stop = entry - stop_distance
        target = entry + reward_risk * stop_distance
    else:
        stop = entry + stop_distance
        target = entry - reward_risk * stop_distance

    risk_per_share = abs(entry - stop)
    reward_per_share = abs(target - entry)
    if risk_per_share <= 0:
        return None

    capital_risk = capital * risk_pct
    shares = int(capital_risk // risk_per_share)
    rr = reward_per_share / risk_per_share

    sentido = "LARGO" if direction > 0 else "CORTO"
    detail = (
        f"{sentido}: entrada {entry:.2f}, stop {stop:.2f} ({atr_mult:g}·ATR), "
        f"objetivo {target:.2f}. R:R={rr:.1f}. "
        f"Arriesgando {risk_pct*100:.1f}% ({capital_risk:.0f}) -> {shares} acciones."
    )
    return TradePlan(
        direction=direction,
        entry=round(entry, 2),
        stop=round(stop, 2),
        target=round(target, 2),
        risk_per_share=round(risk_per_share, 2),
        reward_per_share=round(reward_per_share, 2),
        reward_risk=round(rr, 2),
        shares=shares,
        capital_at_risk=round(capital_risk, 2),
        detail=detail,
    )
