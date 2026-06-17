"""Fachada de alto nivel: analiza un valor de principio a fin.

Une todas las piezas (datos -> indicadores -> consenso -> riesgo -> backtest)
en un único resultado listo para la UI. Es el punto de entrada que usan tanto
la ficha de un valor como el screener.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import backtest, levels as levels_mod, risk
from .consensus import engine
from .consensus.engine import Consensus
from .data import fx, yahoo
from .indicators import technical
from .levels import Level
from .profiles import StrategyProfile
from .qualitative import analysts, fundamentals, sentiment
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
    levels: list[Level] = field(default_factory=list)
    fundamentals: dict = field(default_factory=dict)   # KPIs crudos para la cabecera
    data_warning: str | None = None   # aviso si el análisis se basa en datos pobres
    error: str | None = None

    @property
    def last_price(self) -> float | None:
        if self.df is None or self.df.empty:
            return None
        return float(self.df["Close"].iloc[-1])

    @property
    def n_bars(self) -> int:
        return 0 if self.df is None else len(self.df)

    @property
    def last_date(self):
        if self.df is None or self.df.empty:
            return None
        return self.df.index[-1]


def analyze(
    ticker: str,
    profile: StrategyProfile,
    capital: float = 10_000.0,
    regime: Regime | None = None,
    with_backtest: bool = True,
    with_qualitative: bool = True,
    prices: pd.DataFrame | None = None,
) -> Analysis:
    """Análisis completo de un valor para un perfil de estrategia.

    El análisis (datos, indicadores, consenso) es OBJETIVO y se calcula siempre
    igual: histórico diario. El `profile` solo influye en la dirección del plan
    (largo/corto) y el backtest de su señal, no en el análisis del valor.

    `prices` permite reutilizar un OHLCV ya descargado (p. ej. en lote por el
    screener) y evitar una petición de red por valor.
    """
    raw = prices if (prices is not None and not prices.empty) else yahoo.get_prices(ticker, period="2y", interval="1d")
    if raw is None or raw.empty:
        return Analysis(ticker, ticker, profile, pd.DataFrame(), _empty_consensus(),
                        None, None, error="Sin datos de precios para este valor.")

    df = technical.enrich(raw)

    analyst_view = analysts.from_mean(None)
    sentiment_view = sentiment.analyze([])
    fundamental_view = fundamentals.evaluate(None)
    name = ticker
    fund: dict = {}
    is_us = "." not in ticker          # VADER es inglés: solo fiable en valores US
    if with_qualitative:
        fund = yahoo.get_fundamentals(ticker)
        name = fund.get("name", ticker)
        analyst_view = analysts.from_mean(fund.get("recommendation_mean"), fund.get("num_analysts", 0))
        # Sentimiento solo para US; en otros mercados VADER (inglés) sería ruido.
        if is_us:
            sentiment_view = sentiment.analyze(fund.get("headlines", []))
        else:
            sentiment_view = sentiment.analyze([])
            sentiment_view.detail = "No aplicable (VADER es inglés; titulares no fiables para este mercado)."
        fundamental_view = fundamentals.evaluate(fund, price=float(df["Close"].iloc[-1]))

    cons = engine.evaluate(df, profile, analyst_view, sentiment_view, fundamental_view, regime)

    # Niveles de soporte/resistencia para gráfico y para anclar el riesgo.
    sr_levels = levels_mod.detect(raw)

    # El plan SIEMPRE sigue la dirección de la estrategia elegida:
    # estrategia de corto -> plan bajista (objetivo por DEBAJO de la entrada);
    # estrategias largas -> plan alcista. Así no se mezcla "corto" con objetivo al alza.
    atr = float(df["atr"].iloc[-1]) if not df["atr"].dropna().empty else 0.0
    entry = float(df["Close"].iloc[-1])
    plan_dir = profile.direction
    plan = None
    if atr > 0:
        if plan_dir > 0:
            stop_lv = levels_mod.nearest_support(sr_levels, entry)
            tgt_lv = levels_mod.nearest_resistance(sr_levels, entry)
        else:
            stop_lv = levels_mod.nearest_resistance(sr_levels, entry)
            tgt_lv = levels_mod.nearest_support(sr_levels, entry)
        plan = risk.build_plan(
            entry, atr, plan_dir, capital,
            structure_stop=stop_lv.price if stop_lv else None,
            structure_target=tgt_lv.price if tgt_lv else None,
            fx=fx.to_eur_rate(ticker),
        )

    bt = backtest.run(raw, profile) if with_backtest else None

    # Aviso de calidad/frescura: pocos datos o último dato viejo -> el análisis
    # no es fiable y no debe presentarse como un veredicto firme.
    data_warning = None
    n_bars = len(df)
    if n_bars < 60:
        data_warning = (f"Solo {n_bars} sesiones de histórico: insuficiente para un análisis "
                        "fiable (medias e indicadores incompletos).")
    else:
        try:
            from datetime import datetime, timedelta
            last = df.index[-1].to_pydatetime().replace(tzinfo=None)
            if datetime.now() - last > timedelta(days=7):
                data_warning = (f"Último dato del {last.date()}: posiblemente desactualizado "
                                "(festivo, baja liquidez o problema de la fuente).")
        except Exception:
            pass

    return Analysis(ticker, name, profile, df, cons, plan, bt, levels=sr_levels,
                    fundamentals=fund, data_warning=data_warning)


def _empty_consensus() -> Consensus:
    return Consensus(score=0.0, label="Neutral", confidence=0.0)
