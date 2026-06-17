"""Fixtures: series de precios sintéticas para test offline (sin red)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _ohlcv(closes: np.ndarray, base_vol: float = 1_000_000) -> pd.DataFrame:
    idx = pd.date_range("2022-01-01", periods=len(closes), freq="D")
    close = pd.Series(closes, index=idx)
    high = close * 1.01
    low = close * 0.99
    open_ = close.shift(1).fillna(close.iloc[0])
    vol = pd.Series(np.full(len(closes), base_vol), index=idx)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol})


@pytest.fixture
def uptrend() -> pd.DataFrame:
    n = 400
    closes = 100 * (1 + 0.002) ** np.arange(n) + np.sin(np.arange(n) / 5)
    return _ohlcv(closes)


@pytest.fixture
def downtrend() -> pd.DataFrame:
    n = 400
    closes = 200 * (1 - 0.002) ** np.arange(n) + np.sin(np.arange(n) / 5)
    return _ohlcv(closes)


@pytest.fixture
def flat() -> pd.DataFrame:
    n = 400
    closes = 100 + np.sin(np.arange(n) / 8) * 2
    return _ohlcv(closes)
