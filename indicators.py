"""
ARFEZ AI v3.0 - Ortak Teknik İndikatörler
==========================================
pandas_ta'siz manuel hesaplamalar.
data_collector.py, app_mssql.py ve fair_value_engine.py buradan import eder.
"""
import pandas as pd
import numpy as np


def calc_rsi(series, period=14):
    """Wilder RSI"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calc_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast = calc_ema(series, fast)
    ema_slow = calc_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(macd_line, signal)
    return macd_line, signal_line


def calc_bollinger(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower


def calc_atr(df, period=14):
    """Average True Range"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def calc_relative_volume(df, period=20):
    """Relative Volume (RVOL): son hacim / ortalama hacim."""
    if df is None or len(df) < period:
        return pd.Series([1.0] * (len(df) if df is not None else 0),
                         index=df.index if df is not None else None)

    volume = pd.to_numeric(df['Volume'], errors='coerce')
    avg_volume = volume.rolling(window=period).mean()
    rvol = volume / avg_volume
    return rvol.replace([np.inf, -np.inf], np.nan).fillna(1.0)


def calc_adx(df, period=14):
    """Average Directional Index (basitleştirilmiş)"""
    high = df['High']
    low = df['Low']
    close = df['Close']

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()

    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(window=period).mean()
    return adx
