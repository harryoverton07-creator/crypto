import pandas as pd
import numpy as np

# ---------------------------------------------
# Basic indicator functions
# ---------------------------------------------

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def compute_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def compute_atr(df, period=14):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast = compute_ema(series, fast)
    ema_slow = compute_ema(series, slow)
    macd = ema_fast - ema_slow
    macd_signal = compute_ema(macd, signal)
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist


def compute_volatility(series, window=20):
    returns = series.pct_change()
    return returns.rolling(window).std()


def compute_trend_strength(df):
    return (df["ema20"] > df["ema50"]).astype(int)


# ---------------------------------------------
# Main feature builder
# ---------------------------------------------

def build_features(candles):
    """
    candles: list of dicts from your exchange API
    returns: pandas DataFrame with full feature set
    """

    df = pd.DataFrame(candles)

    # Ensure correct types
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)

    # RSI
    df["rsi"] = compute_rsi(df["close"])

    # EMA
    df["ema20"] = compute_ema(df["close"], 20)
    df["ema50"] = compute_ema(df["close"], 50)

    # ATR
    df["atr"] = compute_atr(df)

    # MACD
    df["macd"], df["macd_signal"], df["macd_hist"] = compute_macd(df["close"])

    # Volatility
    df["volatility"] = compute_volatility(df["close"])

    # Trend strength (1 = bullish, 0 = bearish)
    df["trend_strength"] = compute_trend_strength(df)

    # Drop NaN rows created by rolling windows
    df = df.dropna().reset_index(drop=True)

    return df
