"""Backtest mínimo: ¿esta señal ha ganado dinero históricamente?

Filosofía de Embudo: una señal sin validación es astrología. Este backtest
sencillo recorre el histórico, genera la señal técnica en cada barra y mide el
rendimiento forward a N barras. No pretende ser un motor de trading profesional
(sin comisiones, slippage ni gestión de posición compleja); es un test de
cordura honesto para no fiarse de reglas que nunca han funcionado.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config
from .indicators import technical
from .profiles import StrategyProfile
from .signals import horizons


@dataclass
class BacktestResult:
    n_signals: int
    win_rate: float            # fracción de operaciones con retorno > 0
    avg_return: float          # retorno medio por operación (forward)
    median_return: float
    expectancy: float          # avg_return (proxy de esperanza matemática)
    horizon_bars: int
    detail: str


def run(
    df: pd.DataFrame,
    profile: StrategyProfile,
    horizon_bars: int = 10,
    signal_threshold: float = 0.3,
    warmup: int = 200,
    commission_pct: float = config.DEFAULT_COMMISSION,
) -> BacktestResult:
    """Evalúa la señal técnica del perfil sobre el histórico.

    En cada barra (tras el warmup) calcula el score técnico; si supera el umbral
    en la dirección del perfil, abre una operación virtual y mide el retorno a
    `horizon_bars` barras vista, descontando comisiones de ida y vuelta.
    """
    if df is None or len(df) < warmup + horizon_bars + 5:
        return BacktestResult(0, 0.0, 0.0, 0.0, 0.0, horizon_bars, "Histórico insuficiente para backtest.")

    enriched = technical.enrich(df)
    close = enriched["Close"].to_numpy()
    direction = profile.direction
    returns: list[float] = []

    # Recorremos en pasos para no recalcular en cada barra (rendimiento).
    step = max(1, horizon_bars // 2)
    for i in range(warmup, len(enriched) - horizon_bars, step):
        window = enriched.iloc[: i + 1]
        score = horizons.evaluate(window, profile.horizon).score
        if direction * score >= signal_threshold:
            entry = close[i]
            exit_ = close[i + horizon_bars]
            if entry > 0:
                # Retorno neto: descuenta comisión de entrada y de salida.
                ret = direction * (exit_ - entry) / entry - 2 * commission_pct
                returns.append(ret)

    if not returns:
        return BacktestResult(0, 0.0, 0.0, 0.0, 0.0, horizon_bars, "La señal no se disparó en el histórico.")

    arr = np.array(returns)
    win_rate = float((arr > 0).mean())
    avg = float(arr.mean())
    median = float(np.median(arr))
    detail = (
        f"{len(arr)} señales · acierto {win_rate*100:.0f}% · "
        f"retorno medio {avg*100:+.2f}% a {horizon_bars} barras."
    )
    return BacktestResult(len(arr), round(win_rate, 3), round(avg, 4), round(median, 4),
                          round(avg, 4), horizon_bars, detail)
