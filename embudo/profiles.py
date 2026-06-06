"""Perfiles de estrategia: el selector que define cómo pondera el consenso.

Cuatro estrategias claras (las que elige el usuario) más perfiles ad-hoc:
- Horizonte (Largo / Intraday / Corto) -> elige intervalo/periodo de datos y reglas.
- Pesos por dimensión {tecnico, fundamental, analistas, sentimiento} que suman 1.

Cada preset fija pesos explícitos; los perfiles ad-hoc (p. ej. de tests o del
slider de "enfoque") los derivan del parámetro `focus`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .signals.horizons import Horizon

DIMENSIONS = ("tecnico", "fundamental", "analistas", "sentimiento")


@dataclass
class StrategyProfile:
    horizon: Horizon
    # focus: 0.0 = 100% técnico ... 1.0 = 100% cualitativo (solo para perfiles ad-hoc)
    focus: float = 0.35
    min_rel_volume: float | None = None
    direction: int = 1                          # +1 busca compras, -1 ventas/cortos
    volume_emphasis: bool = False               # sube el peso del volumen (estrategia "seguir el dinero")
    weight_override: dict[str, float] | None = field(default=None)

    @property
    def weights(self) -> dict[str, float]:
        """Pesos normalizados por dimensión (suman 1)."""
        if self.weight_override:
            total = sum(self.weight_override.get(d, 0.0) for d in DIMENSIONS) or 1.0
            return {d: self.weight_override.get(d, 0.0) / total for d in DIMENSIONS}
        # Derivado del slider de enfoque: técnico vs cualitativo (4 dimensiones).
        f = max(0.0, min(1.0, self.focus))
        tech, qual = 1.0 - f, f
        fund_share = 0.5 if self.horizon is Horizon.LARGO else 0.2
        fundamental = qual * fund_share
        rest = qual * (1.0 - fund_share)
        analyst_share = 0.4 if self.horizon is Horizon.CORTO else 0.65
        return {
            "tecnico": tech,
            "fundamental": fundamental,
            "analistas": rest * analyst_share,
            "sentimiento": rest * (1.0 - analyst_share),
        }

    @property
    def interval(self) -> str:
        return {Horizon.LARGO: "1d", Horizon.INTRADAY: "15m", Horizon.CORTO: "1d"}[self.horizon]

    @property
    def period(self) -> str:
        return {Horizon.LARGO: "2y", Horizon.INTRADAY: "60d", Horizon.CORTO: "1y"}[self.horizon]


# Las 4 estrategias seleccionables en el recomendador.
PRESETS: dict[str, StrategyProfile] = {
    "Calidad/Valor (Buffett)": StrategyProfile(
        Horizon.LARGO,
        weight_override={"tecnico": 0.30, "fundamental": 0.45, "analistas": 0.20, "sentimiento": 0.05},
    ),
    "Seguir volumen/momentum": StrategyProfile(
        Horizon.LARGO, min_rel_volume=1.1, volume_emphasis=True,
        weight_override={"tecnico": 0.80, "fundamental": 0.05, "analistas": 0.10, "sentimiento": 0.05},
    ),
    "Intraday técnico": StrategyProfile(
        Horizon.INTRADAY, min_rel_volume=1.2,
        weight_override={"tecnico": 0.90, "fundamental": 0.0, "analistas": 0.05, "sentimiento": 0.05},
    ),
    "Posicionarse a corto / bajista": StrategyProfile(
        Horizon.CORTO, direction=-1,
        weight_override={"tecnico": 0.80, "fundamental": 0.05, "analistas": 0.05, "sentimiento": 0.10},
    ),
}
