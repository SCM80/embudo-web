"""Capa fundamental: calidad/valor al estilo Buffett (gratis, vía Yahoo).

Traduce los fundamentales de una empresa a un score [-1, +1] de "calidad/valor"
con sub-señales explicadas, inspirado en los principios del libro: ventaja
competitiva (proxy: rentabilidad alta y sostenida), poca deuda, buenos márgenes,
crecimiento y precio razonable frente al valor (PER). Degradación elegante: si
faltan datos, peso 0 para no contaminar el consenso (mismo patrón que analysts/
sentiment).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..signals.base import Signal, SignalGroup


@dataclass
class FundamentalView:
    score: float                              # [-1, +1] calidad/valor
    n_metrics: int                            # nº de métricas con datos
    group: SignalGroup = field(default_factory=lambda: SignalGroup("Fundamental"))
    detail: str = ""


def _roe_signal(roe: float | None) -> Signal | None:
    if roe is None:
        return None
    pct = roe * 100
    if pct >= 20:
        return Signal("ROE alto", 0.9, 1.3, f"ROE {pct:.0f}%: rentabilidad excelente (señal de ventaja competitiva).")
    if pct >= 12:
        return Signal("ROE bueno", 0.4, 1.0, f"ROE {pct:.0f}%: rentabilidad sólida.")
    if pct < 5:
        return Signal("ROE bajo", -0.5, 1.0, f"ROE {pct:.0f}%: rentabilidad pobre.")
    return Signal("ROE medio", 0.0, 0.6, f"ROE {pct:.0f}%: rentabilidad mediocre.")


def _debt_signal(de: float | None) -> Signal | None:
    if de is None:
        return None
    # Yahoo da debtToEquity en porcentaje (p.ej. 50 = 0,5x).
    ratio = de / 100.0 if de > 5 else de
    if ratio <= 0.5:
        return Signal("Deuda baja", 0.6, 1.1, f"Deuda/Equity {ratio:.2f}: balance sano, poca deuda.")
    if ratio <= 1.0:
        return Signal("Deuda moderada", 0.1, 0.7, f"Deuda/Equity {ratio:.2f}: deuda razonable.")
    return Signal("Deuda alta", -0.6, 1.1, f"Deuda/Equity {ratio:.2f}: apalancamiento elevado (riesgo).")


def _margin_signal(m: float | None) -> Signal | None:
    if m is None:
        return None
    pct = m * 100
    if pct >= 20:
        return Signal("Márgenes altos", 0.7, 1.0, f"Margen neto {pct:.0f}%: negocio muy rentable.")
    if pct >= 8:
        return Signal("Márgenes buenos", 0.3, 0.8, f"Margen neto {pct:.0f}%: rentable.")
    if pct <= 0:
        return Signal("Sin beneficios", -0.7, 1.0, "Márgenes negativos: la empresa pierde dinero.")
    return Signal("Márgenes ajustados", -0.1, 0.6, f"Margen neto {pct:.0f}%: poco margen.")


def _pe_signal(pe: float | None, growth: float | None) -> Signal | None:
    """Precio vs valor: PER bajo = ganga; PER alto solo se justifica con crecimiento."""
    if pe is None or pe <= 0:
        return None
    if pe < 15:
        return Signal("PER bajo", 0.6, 1.0, f"PER {pe:.0f}: valoración atractiva (posible ganga).")
    if pe <= 25:
        return Signal("PER razonable", 0.1, 0.7, f"PER {pe:.0f}: valoración correcta.")
    # PER alto: aceptable si crece con fuerza (>15%).
    if growth is not None and growth > 0.15:
        return Signal("PER alto con crecimiento", 0.0, 0.7, f"PER {pe:.0f} alto pero el negocio crece ({growth*100:.0f}%).")
    return Signal("PER caro", -0.5, 1.0, f"PER {pe:.0f}: caro frente al valor.")


def _growth_signal(g: float | None) -> Signal | None:
    if g is None:
        return None
    pct = g * 100
    if pct >= 15:
        return Signal("Crecimiento alto", 0.6, 0.9, f"Crecimiento {pct:+.0f}%: negocio en expansión.")
    if pct <= -5:
        return Signal("En contracción", -0.5, 0.9, f"Crecimiento {pct:+.0f}%: ingresos cayendo.")
    return Signal("Crecimiento plano", 0.0, 0.5, f"Crecimiento {pct:+.0f}%.")


def evaluate(fund: dict | None) -> FundamentalView:
    """Construye la vista fundamental a partir del dict de yahoo.get_fundamentals."""
    fund = fund or {}
    group = SignalGroup("Fundamental")
    for sig in (
        _roe_signal(fund.get("roe")),
        _debt_signal(fund.get("debt_to_equity")),
        _margin_signal(fund.get("profit_margins")),
        _pe_signal(fund.get("trailing_pe") or fund.get("forward_pe"),
                   fund.get("earnings_growth") or fund.get("revenue_growth")),
        _growth_signal(fund.get("revenue_growth")),
    ):
        if sig is not None:
            group.add(sig)

    n = len(group.signals)
    if n == 0:
        return FundamentalView(0.0, 0, group, "Sin datos fundamentales disponibles.")
    sentido = "calidad/valor alto" if group.score > 0.2 else "débil" if group.score < -0.2 else "neutro"
    return FundamentalView(group.score, n, group, f"Perfil fundamental {sentido} ({n} métricas).")


def to_signal(view: FundamentalView) -> Signal:
    weight = 0.0 if view.n_metrics == 0 else min(1.5, 0.5 + view.n_metrics / 5.0)
    return Signal("Fundamental", view.score, weight, view.detail)
