"""El recomendador: escanea un universo y rankea candidatos por estrategia.

Es el corazón de Embudo. Dado un universo y un perfil, analiza cada valor con
los pesos del perfil, aplica los filtros duros y devuelve un ranking ordenado
por la dirección buscada (compras para perfiles alcistas, ventas para cortos).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import pandas as pd

from .. import analyzer
from ..analyzer import Analysis
from ..data import universe as universe_data
from ..data import yahoo
from ..profiles import StrategyProfile
from ..regime import Regime, detect


@dataclass
class ScreenRow:
    ticker: str
    name: str
    label: str
    score: float
    confidence: float
    profit_est: float | None   # % estimado hasta el objetivo (profit esperado)
    rr: float | None           # ratio beneficio/riesgo del plan
    reason: str
    rel_volume: float | None


def _passes_filters(analysis: Analysis, profile: StrategyProfile) -> bool:
    if analysis.error or analysis.df.empty:
        return False
    if profile.min_rel_volume is not None:
        rv = analysis.df.get("rel_volume")
        if rv is None or rv.dropna().empty or float(rv.dropna().iloc[-1]) < profile.min_rel_volume:
            return False
    # Filtro de calidad fundamental (p. ej. Calidad/Valor): si hay datos y son malos, fuera.
    if profile.min_quality is not None:
        fv = analysis.consensus.fundamental
        if fv is not None and fv.n_metrics > 0 and fv.score < profile.min_quality:
            return False
    return True


def _top_reason(analysis: Analysis) -> str:
    tech = analysis.consensus.technical
    if tech is None or not tech.signals:
        return analysis.consensus.label
    # La señal con mayor contribución absoluta (peso·score) explica el ranking.
    top = max(tech.signals, key=lambda s: abs(s.score * s.weight))
    return top.reason


def screen(
    universe: Iterable[str],
    profile: StrategyProfile,
    regime: Regime | None = None,
    capital: float = 10_000.0,
    progress: Callable[[int, int, str], None] | None = None,
) -> pd.DataFrame:
    """Analiza cada ticker y devuelve un DataFrame rankeado."""
    tickers = list(universe)
    rows: list[ScreenRow] = []

    # Descarga de precios en un solo lote (rápido y con menos rate-limit).
    batch = yahoo.get_prices_batch(tickers)

    for i, ticker in enumerate(tickers):
        if progress:
            progress(i + 1, len(tickers), ticker)
        try:
            a = analyzer.analyze(ticker, profile, capital=capital, regime=regime,
                                 with_backtest=False, with_qualitative=True,
                                 prices=batch.get(ticker))
        except Exception:
            continue
        if not _passes_filters(a, profile):
            continue
        rv = a.df.get("rel_volume")
        profit_est = rr = None
        if a.trade_plan and a.trade_plan.entry:
            # Profit esperado = recorrido hasta el objetivo, en %.
            profit_est = round(a.trade_plan.reward_per_share / a.trade_plan.entry * 100, 2)
            rr = a.trade_plan.reward_risk
        rows.append(ScreenRow(
            ticker=ticker,
            name=a.name,
            label=a.consensus.label,
            score=a.consensus.score,
            confidence=a.consensus.confidence,
            profit_est=profit_est,
            rr=rr,
            reason=_top_reason(a),
            rel_volume=round(float(rv.dropna().iloc[-1]), 2) if rv is not None and not rv.dropna().empty else None,
        ))

    cols = ["ticker", "name", "label", "score", "confidence", "profit_est", "rr", "reason", "rel_volume"]
    if not rows:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame([r.__dict__ for r in rows])
    # Ranking: para cortos (direction<0) los mejores son los más negativos.
    df = df.sort_values("score", ascending=(profile.direction < 0)).reset_index(drop=True)
    return df


def screen_named(universe_name: str, profile: StrategyProfile, **kwargs) -> tuple[pd.DataFrame, Regime | None]:
    """Versión que resuelve universo + régimen a partir del nombre del universo."""
    tickers = universe_data.get_universe(universe_name)
    index_symbol = universe_data.REGIME_INDEX.get(universe_name)
    regime = None
    if index_symbol:
        idx_df = yahoo.get_prices(index_symbol, period="2y", interval="1d")
        if not idx_df.empty:
            regime = detect(idx_df)
    return screen(tickers, profile, regime=regime, **kwargs), regime
