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
    reason: str
    rel_volume: float | None


def _passes_filters(analysis: Analysis, profile: StrategyProfile) -> bool:
    if analysis.error or analysis.df.empty:
        return False
    if profile.min_rel_volume is not None:
        rv = analysis.df.get("rel_volume")
        if rv is None or rv.dropna().empty or float(rv.dropna().iloc[-1]) < profile.min_rel_volume:
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

    for i, ticker in enumerate(tickers):
        if progress:
            progress(i + 1, len(tickers), ticker)
        try:
            a = analyzer.analyze(ticker, profile, capital=capital, regime=regime,
                                 with_backtest=False, with_qualitative=True)
        except Exception:
            continue
        if not _passes_filters(a, profile):
            continue
        rv = a.df.get("rel_volume")
        rows.append(ScreenRow(
            ticker=ticker,
            name=a.name,
            label=a.consensus.label,
            score=a.consensus.score,
            confidence=a.consensus.confidence,
            reason=_top_reason(a),
            rel_volume=round(float(rv.dropna().iloc[-1]), 2) if rv is not None and not rv.dropna().empty else None,
        ))

    if not rows:
        return pd.DataFrame(columns=["ticker", "name", "label", "score", "confidence", "reason", "rel_volume"])

    df = pd.DataFrame([r.__dict__ for r in rows])
    # Ranking: para cortos (direction<0) los mejores son los más negativos.
    df = df.sort_values("score", ascending=(profile.direction < 0)).reset_index(drop=True)
    return df


def screen_named(universe_name: str, profile: StrategyProfile, **kwargs) -> tuple[pd.DataFrame, Regime | None]:
    """Versión que resuelve universo + régimen a partir del nombre del universo."""
    tickers = universe_data.UNIVERSES.get(universe_name, [])
    index_symbol = universe_data.REGIME_INDEX.get(universe_name)
    regime = None
    if index_symbol:
        idx_df = yahoo.get_prices(index_symbol, period="2y", interval="1d")
        if not idx_df.empty:
            regime = detect(idx_df)
    return screen(tickers, profile, regime=regime, **kwargs), regime
