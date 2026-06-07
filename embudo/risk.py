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
    structure_stop: float | None = None,
    structure_target: float | None = None,
    fx: float = 1.0,
) -> TradePlan | None:
    """Construye un plan de trade. Devuelve None si los datos no son válidos.

    Si se pasa `structure_stop` (p.ej. el soporte más cercano para un largo) y
    es coherente con la dirección, se usa en lugar del stop por ATR — un stop en
    estructura suele ser más fiable que uno ciego. El ATR sigue siendo el
    respaldo cuando no hay nivel válido.
    """
    if not entry or not atr or atr <= 0 or direction == 0:
        return None

    stop_distance = atr_mult * atr
    stop_basis = f"{atr_mult:g}·ATR"
    # Un stop en estructura solo es válido si está RAZONABLEMENTE cerca. En valores
    # muy alcistas el soporte más próximo puede estar lejísimos (p. ej. -75%): eso
    # no es un stop, es arruinarse. Si el nivel está más lejos que este límite,
    # usamos el stop por ATR.
    max_stop_distance = min(max(stop_distance * 1.5, 0.08 * entry), 0.20 * entry)

    if direction > 0:
        stop = entry - stop_distance
        if structure_stop is not None and 0 < (entry - structure_stop) <= max_stop_distance:
            stop = structure_stop * 0.998
            stop_basis = "soporte"
        target = entry + reward_risk * abs(entry - stop)
        if structure_target is not None and structure_target > entry:
            target = structure_target  # resistencia como objetivo natural
    else:
        stop = entry + stop_distance
        if structure_stop is not None and 0 < (structure_stop - entry) <= max_stop_distance:
            stop = structure_stop * 1.002
            stop_basis = "resistencia"
        target = entry - reward_risk * abs(entry - stop)
        if structure_target is not None and 0 < structure_target < entry:
            target = structure_target

    risk_per_share = abs(entry - stop)
    reward_per_share = abs(target - entry)
    if risk_per_share <= 0:
        return None

    capital_risk = capital * risk_pct
    # El riesgo por acción está en la moneda del valor; lo pasamos a la del capital
    # (EUR) con `fx` para que el nº de acciones sea correcto.
    shares = int(capital_risk // (risk_per_share * fx))
    rr = reward_per_share / risk_per_share

    sentido = "LARGO" if direction > 0 else "CORTO"
    detail = (
        f"{sentido}: entrada {entry:.2f}, stop {stop:.2f} ({stop_basis}), "
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
