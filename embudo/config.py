"""Constantes y umbrales centralizados de Embudo.

Mantener aquí los números mágicos hace el sistema auditable y fácil de afinar.
"""
from __future__ import annotations

# --- Mapeo de score [-1, +1] a etiqueta de recomendación ---
LABEL_THRESHOLDS = [
    (0.50, "Compra fuerte"),
    (0.15, "Compra"),
    (-0.15, "Neutral"),
    (-0.50, "Venta"),
]
LABEL_FLOOR = "Venta fuerte"  # por debajo del último umbral


def score_to_label(score: float) -> str:
    """Convierte un score continuo en una etiqueta discreta."""
    for threshold, label in LABEL_THRESHOLDS:
        if score >= threshold:
            return label
    return LABEL_FLOOR


# --- Parámetros de indicadores (valores robustos por defecto) ---
RSI_PERIOD = 14
SMA_FAST = 50
SMA_SLOW = 200
EMA_FAST = 9
EMA_SLOW = 21
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BBANDS_PERIOD = 20
BBANDS_STD = 2.0
ATR_PERIOD = 14
ADX_PERIOD = 14

# --- Gestión de riesgo ---
DEFAULT_RISK_PER_TRADE = 0.01      # 1% del capital por operación
DEFAULT_ATR_STOP_MULT = 2.0        # stop a 2 ATR de la entrada
DEFAULT_REWARD_RISK = 2.0          # objetivo por defecto = 2R
DEFAULT_COMMISSION = 0.0005        # 5 pb por lado (comisión + slippage estimados)

# --- Caché de datos ---
CACHE_DIR = ".embudo_cache"
CACHE_TTL_SECONDS = 60 * 30        # 30 min: equilibrio entre frescura y rate-limit
