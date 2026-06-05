"""Post-mortem: convierte el diario en aprendizaje accionable.

Agrega la estadística de las operaciones cerradas (win rate, esperanza en R,
profit factor, P&L) y, sobre todo, destila **lecciones** sobre los propios
errores: operaciones donde no se respetó el stop, mejores/peores trades, sesgo
por horizonte. El edge del inversor está aquí, no en un indicador más.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .journal import Trade


@dataclass
class Stats:
    n: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_r: float = 0.0              # esperanza matemática en R
    profit_factor: float = 0.0     # ganancias brutas / pérdidas brutas
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0
    best_r: float = 0.0
    worst_r: float = 0.0
    discipline_rate: float = 0.0   # % de trades que respetaron el plan
    by_horizon: dict[str, float] = field(default_factory=dict)  # horizonte -> avg R
    lessons: list[str] = field(default_factory=list)


def summarize(trades: list[Trade]) -> Stats:
    closed = [t for t in trades if t.status == "closed" and t.r_multiple() is not None]
    s = Stats(n=len(closed))
    if not closed:
        s.lessons.append("Aún no hay operaciones cerradas: registra y cierra trades para ver tu estadística.")
        return s

    rs = [t.r_multiple() for t in closed]
    pnls = [t.pnl() or 0.0 for t in closed]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]

    s.wins, s.losses = len(wins), len(losses)
    s.win_rate = round(len(wins) / len(closed), 3)
    s.total_pnl = round(sum(pnls), 2)
    s.avg_r = round(sum(rs) / len(rs), 2)
    s.best_r, s.worst_r = round(max(rs), 2), round(min(rs), 2)
    s.avg_win_r = round(sum(wins) / len(wins), 2) if wins else 0.0
    s.avg_loss_r = round(sum(losses) / len(losses), 2) if losses else 0.0

    gross_win = sum(r for r in rs if r > 0)
    gross_loss = abs(sum(r for r in rs if r < 0))
    s.profit_factor = round(gross_win / gross_loss, 2) if gross_loss > 0 else float("inf")

    disciplined = [t for t in closed if t.followed_plan()]
    s.discipline_rate = round(len(disciplined) / len(closed), 3)

    by_h: dict[str, list[float]] = {}
    for t in closed:
        by_h.setdefault(t.horizon or "—", []).append(t.r_multiple())
    s.by_horizon = {h: round(sum(v) / len(v), 2) for h, v in by_h.items()}

    s.lessons = _lessons(s, closed)
    return s


def _lessons(s: Stats, closed: list[Trade]) -> list[str]:
    out: list[str] = []
    if s.avg_r > 0:
        out.append(f"✅ Esperanza positiva: ganas {s.avg_r:+.2f}R de media por operación.")
    else:
        out.append(f"⚠️ Esperanza negativa ({s.avg_r:+.2f}R): el sistema/operativa pierde dinero a largo plazo.")

    if s.discipline_rate < 0.8:
        broke = [t.ticker for t in closed if not t.followed_plan()]
        out.append(f"🔴 Disciplina baja ({s.discipline_rate*100:.0f}%): no respetaste el stop en {', '.join(broke[:5])}.")
    else:
        out.append(f"🟢 Buena disciplina: respetaste el plan en el {s.discipline_rate*100:.0f}% de los trades.")

    if s.win_rate < 0.4 and s.avg_r > 0:
        out.append("📌 Pocos aciertos pero rentable: dejas correr ganadores y cortas pérdidas. Bien.")
    if s.win_rate > 0.6 and s.avg_r < 0:
        out.append("📌 Aciertas mucho pero pierdes: tus pérdidas son demasiado grandes frente a tus ganancias.")

    if s.by_horizon:
        best = max(s.by_horizon, key=s.by_horizon.get)
        worst = min(s.by_horizon, key=s.by_horizon.get)
        if best != worst:
            out.append(f"🎯 Tu mejor horizonte es «{best}» ({s.by_horizon[best]:+.2f}R) y el peor «{worst}» ({s.by_horizon[worst]:+.2f}R).")
    return out
