"""Perfiles de estrategia: el selector que define cómo pondera el consenso.

Dos ejes:
- Horizonte (Largo / Intraday / Corto) -> elige el intervalo de datos y las reglas.
- Enfoque (técnico <-> cualitativo) -> reparte el peso entre dimensiones.

Un perfil traduce las preferencias del usuario en pesos y filtros concretos.
"""
from __future__ import annotations

from dataclasses import dataclass

from .signals.horizons import Horizon


@dataclass
class StrategyProfile:
    horizon: Horizon
    # focus: 0.0 = 100% técnico ... 1.0 = 100% cualitativo
    focus: float = 0.35
    # Filtros duros del screener (None = no aplica)
    min_rel_volume: float | None = None
    # Para cortos buscamos señales negativas; para el resto, positivas.
    direction: int = 1  # +1 = busca compras, -1 = busca ventas/cortos

    @property
    def weights(self) -> dict[str, float]:
        """Reparte peso entre técnico y cualitativo (analistas+sentimiento)."""
        f = max(0.0, min(1.0, self.focus))
        tech = 1.0 - f
        qual = f
        # En cortos, los analistas (sesgo comprador estructural) pesan menos.
        analyst_share = 0.4 if self.horizon is Horizon.CORTO else 0.65
        return {
            "tecnico": tech,
            "analistas": qual * analyst_share,
            "sentimiento": qual * (1.0 - analyst_share),
        }

    @property
    def interval(self) -> str:
        """Intervalo de velas de Yahoo adecuado al horizonte."""
        return {
            Horizon.LARGO: "1d",
            Horizon.INTRADAY: "15m",
            Horizon.CORTO: "1d",
        }[self.horizon]

    @property
    def period(self) -> str:
        """Ventana de histórico a descargar."""
        return {
            Horizon.LARGO: "2y",
            Horizon.INTRADAY: "60d",   # Yahoo limita intradía a ~60 días
            Horizon.CORTO: "1y",
        }[self.horizon]


# Presets listos para la UI.
PRESETS: dict[str, StrategyProfile] = {
    "Inversión a largo (mixto)": StrategyProfile(Horizon.LARGO, focus=0.4),
    "Largo · solo técnico": StrategyProfile(Horizon.LARGO, focus=0.0),
    "Largo · solo cualitativo": StrategyProfile(Horizon.LARGO, focus=0.9),
    "Intraday (técnico)": StrategyProfile(Horizon.INTRADAY, focus=0.1, min_rel_volume=1.2),
    "Posicionarse a corto / bajista": StrategyProfile(Horizon.CORTO, focus=0.3, direction=-1),
}
