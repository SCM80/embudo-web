"""Fachada de alto nivel: analiza un valor de principio a fin.

Une todas las piezas (datos -> indicadores -> consenso -> riesgo -> backtest)
en un único resultado listo para la UI. Es el punto de entrada que usan tanto
la ficha de un valor como el screener.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import backtest, risk
from .consensus import engine
from .consensus.engine import Consensus
from .data import yahoo
from .indicators import technical
from .profiles import StrategyProfile
from .qualitative import analysts, sentiment
from .regime import Regime


@dataclass
class Analysis:
    ticker: str
    name: str
    profile: StrategyProfile
    df: pd.DataFrame                  # OHLCV enriquecido con indicadores
    consensus: Consensus
    trade_plan: risk.TradePlan | None
    backtest: backtest.BacktestResult | None
    error: str | None = None

    @property
    def last_price(self) -> float | None:
        if self.df is None or self.df.empty:
            return None
        return float(self.df["Close"].iloc[-1])


def analyze(
    ticker: str,
    profile: StrategyProfile,
    capital: float = 10_000.0,
    regime: Regime | None = None,
    with_backtest: bool = True,
    with_qualitative: bool = True,
) -> Analysis:
    """Análisis completo de un valor para un perfil de estrategia."""
    raw = yahoo.get_prices(ticker, period=profile.period, interval=profile.interval)
    if raw is None or raw.empty:
        return Analysis(ticker, ticker, profile, pd.DataFrame(), _empty_consensus(),
                        None, None, error="Sin datos de precios para este valor.")

    df = technical.enrich(raw)

    analyst_view = analysts.from_mean(None)
    sentiment_view = sentiment.analyze([])
    name = ticker
    if with_qualitative:
        fund = yahoo.get_fundamentals(ticker)
        name = fund.get("name", ticker)
        analyst_view = analysts.from_mean(fund.get("recommendation_mean"), fund.get("num_analysts", 0))
        sentiment_view = sentiment.analyze(fund.get("headlines", []))

    cons = engine.evaluate(df, profile, analyst_view, sentiment_view, regime)

    # Plan de riesgo en la dirección de la señal (o la del perfil para cortos).
    atr = float(df["atr"].iloc[-1]) if not df["atr"].dropna().empty else 0.0
    entry = float(df["Close"].iloc[-1])
    plan_dir = cons.direction if cons.direction != 0 else profile.direction
    plan = risk.build_plan(entry, atr, plan_dir, capital) if atr > 0 else None

    bt = backtest.run(raw, profile) if with_backtest else None

    return Analysis(ticker, name, profile, df, cons, plan, bt)


def _empty_consensus() -> Consensus:
    return Consensus(score=0.0, label="Neutral", confidence=0.0)
