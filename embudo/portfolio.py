"""Vista de cartera: exposición, concentración y correlación de las posiciones.

Usa las operaciones abiertas del diario para avisar de riesgos que no se ven
mirando una acción aislada: demasiada exposición, una posición demasiado grande
o varias posiciones muy correlacionadas (riesgo concentrado encubierto).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ProposedPosition:
    ticker: str
    name: str
    weight: float          # fracción del capital asignada
    amount: float          # importe asignado (capital * weight)
    price: float           # precio actual (entrada)
    shares: int
    label: str             # señal del consenso


def generate(candidates: pd.DataFrame, capital: float, n: int = 5,
             method: str = "score") -> list[ProposedPosition]:
    """Propone una cartera con los `n` mejores candidatos del escáner.

    `method`:
      - "equal": equiponderada.
      - "score": peso proporcional a la fuerza de la señal (score positivo).
      - "riesgo": menor peso a más volatilidad (proxy: 1/|profit_est|, acota concentración).
    El precio de entrada se toma de la columna 'price' si existe; si no, se omite
    la posición (no se puede dimensionar sin precio).
    """
    if candidates is None or candidates.empty or capital <= 0 or n <= 0:
        return []
    df = candidates.head(n).copy()

    if method == "equal":
        df["_w"] = 1.0
    elif method == "riesgo":
        pe = df.get("profit_est")
        df["_w"] = (1.0 / pe.abs().clip(lower=1.0)) if pe is not None else 1.0
    else:  # "score": proporcional a la fuerza de la señal
        df["_w"] = df["score"].abs().clip(lower=0.01) if "score" in df else 1.0

    total = float(df["_w"].sum()) or 1.0
    out: list[ProposedPosition] = []
    for _, row in df.iterrows():
        price = row.get("price")
        if price is None or pd.isna(price) or float(price) <= 0:
            continue
        price = float(price)
        w = float(row["_w"]) / total
        amount = round(capital * w, 2)
        out.append(ProposedPosition(
            ticker=row.get("ticker", ""),
            name=row.get("name", row.get("ticker", "")),
            weight=round(w, 3),
            amount=amount,
            price=round(price, 2),
            shares=int(amount // price),
            label=row.get("label", ""),
        ))
    return out


@dataclass
class Position:
    ticker: str
    direction: int
    notional: float        # tamaño en moneda del valor (acciones × entrada)
    weight: float          # % sobre el capital


@dataclass
class PortfolioView:
    capital: float
    positions: list[Position] = field(default_factory=list)
    gross_exposure: float = 0.0     # % del capital invertido (bruto)
    net_exposure: float = 0.0       # % neto (largos - cortos)
    warnings: list[str] = field(default_factory=list)


def summarize(open_trades, capital: float, max_position: float = 0.25,
              max_gross: float = 1.0) -> PortfolioView:
    pv = PortfolioView(capital=capital)
    if capital <= 0:
        return pv
    gross = net = 0.0
    for t in open_trades:
        notional = t.shares * t.entry
        w = notional / capital
        pv.positions.append(Position(t.ticker, t.direction, round(notional, 2), round(w, 3)))
        gross += w
        net += w * (1 if t.direction > 0 else -1)
        if w > max_position:
            pv.warnings.append(f"⚠️ {t.ticker} pesa {w*100:.0f}% del capital (> {max_position*100:.0f}%): posición grande.")
    pv.gross_exposure = round(gross, 3)
    pv.net_exposure = round(net, 3)
    if gross > max_gross:
        pv.warnings.append(f"⚠️ Exposición bruta {gross*100:.0f}% (> {max_gross*100:.0f}%): estás muy invertido/apalancado.")
    if not pv.warnings and pv.positions:
        pv.warnings.append("🟢 Exposición y concentración dentro de límites razonables.")
    return pv


def correlations(prices: dict[str, pd.DataFrame], threshold: float = 0.7) -> list[tuple[str, str, float]]:
    """Pares de posiciones con correlación de retornos diaria alta (riesgo concentrado)."""
    rets = {}
    for t, df in prices.items():
        if df is not None and len(df) > 30:
            rets[t] = df["Close"].pct_change().dropna()
    if len(rets) < 2:
        return []
    mat = pd.DataFrame(rets).dropna()
    if len(mat) < 20:
        return []
    corr = mat.corr()
    out = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            c = float(corr.iloc[i, j])
            if c >= threshold:
                out.append((cols[i], cols[j], round(c, 2)))
    return sorted(out, key=lambda x: -x[2])
