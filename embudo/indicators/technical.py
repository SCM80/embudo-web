"""Indicadores técnicos en pandas/numpy puro.

Implementados a mano a propósito: cero dependencias que compilen (sin TA-Lib),
totalmente testeable sin red y sin sorpresas de versiones. Cada función recibe
Series/DataFrame de precios y devuelve Series/DataFrame alineados por índice.

Convención de columnas OHLCV: 'Open', 'High', 'Low', 'Close', 'Volume'.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import config


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period, min_periods=period).mean()


def ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(close: pd.Series, period: int = config.RSI_PERIOD) -> pd.Series:
    """RSI de Wilder (suavizado exponencial con alpha = 1/period)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100 - (100 / (1 + rs))
    # Si no hubo pérdidas, RSI satura a 100; si no hubo ganancias, a 0.
    out = out.where(avg_loss != 0, 100.0)
    out = out.where(avg_gain != 0, out.where(avg_loss != 0, 50.0))
    return out


def macd(
    close: pd.Series,
    fast: int = config.MACD_FAST,
    slow: int = config.MACD_SLOW,
    signal: int = config.MACD_SIGNAL,
) -> pd.DataFrame:
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def bollinger(
    close: pd.Series,
    period: int = config.BBANDS_PERIOD,
    n_std: float = config.BBANDS_STD,
) -> pd.DataFrame:
    mid = sma(close, period)
    std = close.rolling(period, min_periods=period).std(ddof=0)
    upper = mid + n_std * std
    lower = mid - n_std * std
    width = (upper - lower) / mid
    pct_b = (close - lower) / (upper - lower).replace(0.0, np.nan)
    return pd.DataFrame(
        {"bb_mid": mid, "bb_upper": upper, "bb_lower": lower, "bb_width": width, "bb_pct": pct_b}
    )


def true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr


def atr(df: pd.DataFrame, period: int = config.ATR_PERIOD) -> pd.Series:
    """Average True Range (Wilder)."""
    tr = true_range(df)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def adx(df: pd.DataFrame, period: int = config.ADX_PERIOD) -> pd.DataFrame:
    """ADX + DI+/DI- (Wilder). Mide fuerza de tendencia (no dirección)."""
    high, low = df["High"], df["Low"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    atr_ = true_range(df).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr_
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr_
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx_ = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return pd.DataFrame({"adx": adx_, "plus_di": plus_di, "minus_di": minus_di})


def obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume: volumen acumulado según el signo del cambio de precio."""
    direction = np.sign(df["Close"].diff().fillna(0.0))
    return (direction * df["Volume"]).cumsum()


def relative_volume(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Volumen actual / volumen medio reciente. >1 = sesión más activa de lo normal."""
    avg = df["Volume"].rolling(period, min_periods=period).mean()
    return df["Volume"] / avg.replace(0.0, np.nan)


def vwap(df: pd.DataFrame) -> pd.Series:
    """VWAP (Volume Weighted Average Price) con reinicio por sesión diaria.

    Referencia clave del intradía: si el precio está sobre el VWAP, los
    compradores dominan la sesión. Para datos diarios o sin marca de tiempo
    intradía, calcula un VWAP acumulado global (degradación elegante).
    """
    typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
    pv = typical * df["Volume"]
    try:
        days = df.index.normalize()  # reinicio por día natural (intradía)
        cum_pv = pv.groupby(days).cumsum()
        cum_vol = df["Volume"].groupby(days).cumsum()
    except (AttributeError, TypeError):
        cum_pv = pv.cumsum()
        cum_vol = df["Volume"].cumsum()
    return cum_pv / cum_vol.replace(0.0, np.nan)


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Añade todos los indicadores a un DataFrame OHLCV y lo devuelve."""
    out = df.copy()
    close = out["Close"]
    out["sma_fast"] = sma(close, config.SMA_FAST)
    out["sma_slow"] = sma(close, config.SMA_SLOW)
    out["ema_fast"] = ema(close, config.EMA_FAST)
    out["ema_slow"] = ema(close, config.EMA_SLOW)
    out["rsi"] = rsi(close)
    out = out.join(macd(close))
    out = out.join(bollinger(close))
    out["atr"] = atr(out)
    out = out.join(adx(out))
    out["obv"] = obv(out)
    out["rel_volume"] = relative_volume(out)
    out["vwap"] = vwap(out)
    return out
