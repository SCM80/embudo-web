"""Tests de los indicadores técnicos sobre series sintéticas."""
from __future__ import annotations

import numpy as np
import pandas as pd

from embudo.indicators import technical


def test_rsi_bounds(uptrend):
    rsi = technical.rsi(uptrend["Close"]).dropna()
    assert ((rsi >= 0) & (rsi <= 100)).all()


def test_rsi_high_in_uptrend(uptrend):
    rsi = technical.rsi(uptrend["Close"]).dropna()
    assert rsi.iloc[-1] > 55  # tendencia alcista -> RSI elevado


def test_sma_ema_track_price(uptrend):
    sma = technical.sma(uptrend["Close"], 50).dropna()
    assert (sma.diff().dropna() > 0).mean() > 0.9  # SMA creciente en uptrend


def test_macd_positive_in_uptrend(uptrend):
    macd = technical.macd(uptrend["Close"]).dropna()
    assert macd["macd"].iloc[-1] > 0


def test_atr_positive(uptrend):
    atr = technical.atr(uptrend).dropna()
    assert (atr > 0).all()


def test_enrich_adds_columns(uptrend):
    df = technical.enrich(uptrend)
    for col in ("sma_fast", "sma_slow", "rsi", "macd", "atr", "adx", "obv", "rel_volume"):
        assert col in df.columns


def test_adx_in_range(uptrend):
    adx = technical.adx(uptrend)["adx"].dropna()
    assert ((adx >= 0) & (adx <= 100)).all()
