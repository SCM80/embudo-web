"""Alertas: reglas que se evalúan bajo demanda contra los datos actuales.

Sin servicio en segundo plano (mantenemos el coste a cero): las alertas se
comprueban cuando el usuario pulsa "revisar". Cada regla describe una condición
(precio, RSI, cruce de media o cambio de señal) sobre un ticker. Persistencia en
JSON local.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from . import config
from .indicators import technical

_PATH = Path(config.CACHE_DIR) / "alerts.json"

KINDS = {
    "price_above": "Precio por encima de",
    "price_below": "Precio por debajo de",
    "rsi_above": "RSI por encima de",
    "rsi_below": "RSI por debajo de",
    "cross_above_sma200": "Precio cruza al alza la SMA200",
    "cross_below_sma200": "Precio cruza a la baja la SMA200",
}


@dataclass
class AlertRule:
    ticker: str
    kind: str
    value: float = 0.0
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def describe(self) -> str:
        label = KINDS.get(self.kind, self.kind)
        if self.kind.startswith("cross"):
            return f"{self.ticker}: {label}"
        return f"{self.ticker}: {label} {self.value:g}"


@dataclass
class AlertHit:
    rule: AlertRule
    triggered: bool
    message: str


def _to_rule(d: dict) -> AlertRule:
    fields = set(AlertRule.__dataclass_fields__)
    return AlertRule(**{k: v for k, v in d.items() if k in fields})


def load() -> list[AlertRule]:
    try:
        if _PATH.exists():
            return [_to_rule(d) for d in json.loads(_PATH.read_text(encoding="utf-8"))]
    except Exception:
        pass
    return []


def save(rules: list[AlertRule]) -> None:
    try:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        _PATH.write_text(json.dumps([asdict(r) for r in rules], ensure_ascii=False, indent=2),
                         encoding="utf-8")
    except Exception:
        pass


def add(rule: AlertRule) -> list[AlertRule]:
    rules = load()
    rules.append(rule)
    save(rules)
    return rules


def remove(rule_id: str) -> list[AlertRule]:
    rules = [r for r in load() if r.id != rule_id]
    save(rules)
    return rules


def check_all(rules: list[AlertRule] | None = None) -> list[AlertHit]:
    """Descarga datos por ticker (una vez) y evalúa todas las reglas activas."""
    from .data import yahoo

    rules = rules if rules is not None else load()
    cache: dict[str, pd.DataFrame] = {}
    hits: list[AlertHit] = []
    for rule in rules:
        if rule.ticker not in cache:
            cache[rule.ticker] = yahoo.get_prices(rule.ticker, period="1y", interval="1d")
        hits.append(evaluate(rule, cache[rule.ticker]))
    return hits


def evaluate(rule: AlertRule, df: pd.DataFrame) -> AlertHit:
    """Comprueba una regla contra un DataFrame OHLCV (ya con o sin indicadores)."""
    if df is None or df.empty:
        return AlertHit(rule, False, f"{rule.ticker}: sin datos.")
    enriched = technical.enrich(df) if "rsi" not in df.columns else df
    close = float(enriched["Close"].iloc[-1])
    prev = float(enriched["Close"].iloc[-2]) if len(enriched) > 1 else close

    triggered, msg = False, ""
    if rule.kind == "price_above":
        triggered = close > rule.value
        msg = f"{rule.ticker}: precio {close:.2f} {'>' if triggered else '≤'} {rule.value:g}"
    elif rule.kind == "price_below":
        triggered = close < rule.value
        msg = f"{rule.ticker}: precio {close:.2f} {'<' if triggered else '≥'} {rule.value:g}"
    elif rule.kind in ("rsi_above", "rsi_below"):
        rsi = enriched["rsi"].dropna()
        if rsi.empty:
            return AlertHit(rule, False, f"{rule.ticker}: RSI no disponible.")
        rv = float(rsi.iloc[-1])
        triggered = rv > rule.value if rule.kind == "rsi_above" else rv < rule.value
        msg = f"{rule.ticker}: RSI {rv:.0f} ({'cumple' if triggered else 'no cumple'})"
    elif rule.kind in ("cross_above_sma200", "cross_below_sma200"):
        sma = enriched["sma_slow"]
        if sma.dropna().empty or len(sma) < 2:
            return AlertHit(rule, False, f"{rule.ticker}: SMA200 no disponible.")
        s_now, s_prev = float(sma.iloc[-1]), float(sma.iloc[-2])
        if rule.kind == "cross_above_sma200":
            triggered = prev <= s_prev and close > s_now
        else:
            triggered = prev >= s_prev and close < s_now
        msg = f"{rule.ticker}: {'✅ cruce confirmado' if triggered else 'sin cruce'} (SMA200 {s_now:.2f})"
    return AlertHit(rule, triggered, msg)
