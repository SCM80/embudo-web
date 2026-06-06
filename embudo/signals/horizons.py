"""Reglas técnicas específicas por horizonte temporal.

Cada horizonte mira el mercado con otra lente:
- LARGO: tendencia primaria y momentum sostenido.
- INTRADAY: cruces rápidos de EMA y volumen relativo.
- CORTO (bajista): sobrecompra, debilidad y agotamiento.

Devuelve un SignalGroup técnico ya combinado con tendencia y volumen.
"""
from __future__ import annotations

from enum import Enum

import pandas as pd

from .. import levels as levels_mod
from . import trend, volume
from .base import Signal, SignalGroup


class Horizon(str, Enum):
    LARGO = "Largo plazo"
    INTRADAY = "Intraday"
    CORTO = "Corto / bajista"


def _last(df: pd.DataFrame, col: str) -> float | None:
    s = df.get(col)
    if s is None or s.dropna().empty:
        return None
    return float(s.dropna().iloc[-1])


def _rsi_signal(rsi: float | None, horizon: Horizon) -> Signal | None:
    if rsi is None:
        return None
    if horizon is Horizon.CORTO:
        # Para cortos buscamos sobrecompra (agotamiento al alza).
        if rsi >= 70:
            return Signal("RSI sobrecompra", -0.7, 1.2, f"RSI={rsi:.0f}: sobrecompra, riesgo de corrección.")
        if rsi <= 50:
            return Signal("RSI débil", -0.3, 0.8, f"RSI={rsi:.0f}: momentum débil.")
        return None
    # Largo / intraday: sobreventa = oportunidad, sobrecompra = cautela.
    if rsi <= 30:
        return Signal("RSI sobreventa", 0.7, 1.2, f"RSI={rsi:.0f}: sobreventa, posible rebote.")
    if rsi >= 70:
        return Signal("RSI sobrecompra", -0.4, 1.0, f"RSI={rsi:.0f}: sobrecompra, cautela.")
    return None


def _support_breakdown(df: pd.DataFrame, lookback: int = 60) -> Signal | None:
    """Detecta si el precio acaba de perder un soporte relevante (señal bajista)."""
    recent = df.iloc[-lookback:] if len(df) > lookback else df
    lv = levels_mod.detect(recent)
    close = _last(df, "Close")
    prev = float(df["Close"].iloc[-2]) if len(df) > 1 else close
    if close is None:
        return None
    support = levels_mod.nearest_support(lv, prev)
    # Antes el precio estaba por encima del soporte y ahora lo ha perdido.
    if support is not None and prev >= support.price > close:
        return Signal("Ruptura de soporte", -0.8, 1.4,
                      f"Pérdida del soporte en {support.price:.2f} ({support.strength}): confirmación bajista.")
    return None


def evaluate(df: pd.DataFrame, horizon: Horizon, volume_emphasis: bool = False) -> SignalGroup:
    """Construye el grupo técnico para el horizonte indicado.

    `volume_emphasis` (estrategia "seguir el dinero") sube el peso de las señales
    de volumen para priorizar el rastro del capital institucional.
    """
    group = SignalGroup(f"Técnico · {horizon.value}")

    # Base común: tendencia + volumen (con pesos según horizonte).
    trend_group = trend.evaluate(df)
    volume_group = volume.evaluate(df)

    if volume_emphasis:
        for s in volume_group.signals:
            s.weight *= 1.8  # priorizar el rastro del dinero (volumen/OBV/divergencias)

    if horizon is Horizon.LARGO:
        for s in trend_group.signals:
            s.weight *= 1.3  # la tendencia manda en el largo
        for s in volume_group.signals:
            s.weight *= 0.7
    elif horizon is Horizon.INTRADAY:
        for s in volume_group.signals:
            s.weight *= 1.3  # el volumen manda en intraday
        # Cruce rápido EMA9/EMA21.
        ema_fast = _last(df, "ema_fast")
        ema_slow = _last(df, "ema_slow")
        if ema_fast is not None and ema_slow is not None:
            if ema_fast > ema_slow:
                group.add(Signal("EMA9 > EMA21", 0.6, 1.4, "Cruce rápido alcista: momentum intradía positivo."))
            else:
                group.add(Signal("EMA9 < EMA21", -0.6, 1.4, "Cruce rápido bajista: momentum intradía negativo."))
        # VWAP: referencia intradía clave (compradores vs vendedores de la sesión).
        close = _last(df, "Close")
        vwap = _last(df, "vwap")
        if close is not None and vwap is not None and vwap > 0:
            dist = (close - vwap) / vwap
            if close >= vwap:
                group.add(Signal("Precio > VWAP", min(1.0, 0.5 + abs(dist) * 10), 1.3,
                                 f"Precio sobre el VWAP ({dist*100:+.1f}%): control comprador en la sesión."))
            else:
                group.add(Signal("Precio < VWAP", -min(1.0, 0.5 + abs(dist) * 10), 1.3,
                                 f"Precio bajo el VWAP ({dist*100:+.1f}%): control vendedor en la sesión."))
    elif horizon is Horizon.CORTO:
        # Para cortos invertimos la lectura: penaliza la fortaleza, premia la debilidad.
        for s in trend_group.signals:
            s.weight *= 1.1
        # Pérdida de banda inferior de Bollinger / cierre bajo media.
        bb_pct = _last(df, "bb_pct")
        if bb_pct is not None and bb_pct >= 1.0:
            group.add(Signal("Fuera Bollinger sup.", -0.6, 1.2, "Precio sobre la banda superior: extensión, riesgo de reversión."))
        # Ruptura de soporte: la confirmación bajista más fiable para un corto.
        breakdown = _support_breakdown(df)
        if breakdown is not None:
            group.add(breakdown)

    group.signals.extend(trend_group.signals)
    group.signals.extend(volume_group.signals)

    rsi_sig = _rsi_signal(_last(df, "rsi"), horizon)
    if rsi_sig:
        group.add(rsi_sig)

    return group
