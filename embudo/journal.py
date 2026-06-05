"""Diario de operaciones + post-mortem (el bucle de aprendizaje).

Registra cada operación con su *tesis* (el porqué de la entrada), y al cerrarla
calcula P&L, R-múltiplo y si se respetó el plan. El post-mortem agrega la
estadística de TUS decisiones: ahí está la mejora real, más que en cualquier
indicador. Persistencia en JSON local, sin servicios externos.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from . import config

_PATH = Path(config.CACHE_DIR) / "journal.json"


@dataclass
class Trade:
    ticker: str
    direction: int                 # +1 largo, -1 corto
    entry: float
    stop: float
    target: float
    shares: int
    horizon: str = ""
    thesis: str = ""               # por qué entraste (clave para el post-mortem)
    opened_at: str = field(default_factory=lambda: date.today().isoformat())
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    # Cierre
    status: str = "open"           # "open" | "closed"
    exit: float | None = None
    closed_at: str | None = None
    exit_reason: str = ""

    # --- Métricas derivadas (se calculan, no se persisten redundantes) ---
    @property
    def risk_per_share(self) -> float:
        return abs(self.entry - self.stop)

    def pnl(self, commission_pct: float = config.DEFAULT_COMMISSION) -> float | None:
        """P&L realizado neto de comisiones (ida y vuelta)."""
        if self.exit is None:
            return None
        gross = self.direction * (self.exit - self.entry) * self.shares
        cost = commission_pct * self.shares * (self.entry + self.exit)
        return round(gross - cost, 2)

    def pnl_pct(self) -> float | None:
        if self.exit is None or self.entry == 0:
            return None
        return round(self.direction * (self.exit - self.entry) / self.entry * 100, 2)

    def r_multiple(self) -> float | None:
        """Resultado en múltiplos de riesgo (R). +2R = ganaste el doble del riesgo."""
        if self.exit is None or self.risk_per_share == 0:
            return None
        return round(self.direction * (self.exit - self.entry) / self.risk_per_share, 2)

    def followed_plan(self) -> bool | None:
        """¿Se respetó el stop? Salir muy por debajo del stop (largo) = indisciplina."""
        if self.exit is None:
            return None
        if self.direction > 0:
            return self.exit >= self.stop * 0.99
        return self.exit <= self.stop * 1.01


def _to_trade(d: dict) -> Trade:
    fields = {f for f in Trade.__dataclass_fields__}
    return Trade(**{k: v for k, v in d.items() if k in fields})


def load() -> list[Trade]:
    try:
        if _PATH.exists():
            data = json.loads(_PATH.read_text(encoding="utf-8"))
            return [_to_trade(d) for d in data]
    except Exception:
        pass
    return []


def save(trades: list[Trade]) -> None:
    try:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        _PATH.write_text(json.dumps([asdict(t) for t in trades], ensure_ascii=False, indent=2),
                         encoding="utf-8")
    except Exception:
        pass


def add(trade: Trade) -> list[Trade]:
    trades = load()
    trades.append(trade)
    save(trades)
    return trades


def close(trade_id: str, exit_price: float, reason: str = "") -> list[Trade]:
    trades = load()
    for t in trades:
        if t.id == trade_id and t.status == "open":
            t.status = "closed"
            t.exit = float(exit_price)
            t.closed_at = date.today().isoformat()
            t.exit_reason = reason
    save(trades)
    return trades


def remove(trade_id: str) -> list[Trade]:
    trades = [t for t in load() if t.id != trade_id]
    save(trades)
    return trades


def open_trades() -> list[Trade]:
    return [t for t in load() if t.status == "open"]


def closed_trades() -> list[Trade]:
    return [t for t in load() if t.status == "closed"]
