"""Estructura común de una señal explicable.

Principio de diseño: nunca un score sin su *por qué*. Cada señal lleva su
contribución numérica [-1, +1] y un texto legible para el humano.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Signal:
    """Una lectura individual del mercado.

    score: contribución en [-1, +1] (negativo = bajista, positivo = alcista).
    weight: importancia relativa dentro de su grupo (>= 0).
    reason: explicación legible de por qué se dispara.
    """

    name: str
    score: float
    weight: float = 1.0
    reason: str = ""

    def __post_init__(self) -> None:
        self.score = float(max(-1.0, min(1.0, self.score)))
        self.weight = float(max(0.0, self.weight))


@dataclass
class SignalGroup:
    """Conjunto de señales de una misma dimensión (técnica, volumen, etc.)."""

    name: str
    signals: list[Signal] = field(default_factory=list)

    def add(self, signal: Signal) -> None:
        self.signals.append(signal)

    @property
    def score(self) -> float:
        """Media ponderada de las señales del grupo, en [-1, +1]."""
        total_w = sum(s.weight for s in self.signals)
        if total_w == 0:
            return 0.0
        return sum(s.score * s.weight for s in self.signals) / total_w

    @property
    def bullish(self) -> list[Signal]:
        return [s for s in self.signals if s.score > 0]

    @property
    def bearish(self) -> list[Signal]:
        return [s for s in self.signals if s.score < 0]
