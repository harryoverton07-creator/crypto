import requests
import time
import json
import os
from datetime import datetime

# Kraken interval map (in minutes)
INTERVAL_MAP = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "1h": 60,
    "4h": 240,
    "1d": 1440
}

# Kraken pair map
PAIR_MAP = {
    "BTC": "XBTUSD",
    "ETH": "ETHUSD",
    "SOL": "SOLUSD",
    "XRP": "XRPUSD",
    "ADA": "ADAUSD"
}

CACHE_DIR = "history/candles"
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_kraken_ohlc(coin: str, interval: str = "15m", limit: int = 500):
    """
    Fetches OHLCV candles from Kraken.
    interval: "1m", "5m", "15m", "1h", "4h", "1d"
    limit: number of candles to return
    """

    pair = PAIR_MAP.get(coin)
    if not pair:
        return []

    kraken_interval = INTERVAL_MAP[interval]

    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={kraken_interval}"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        result = list(data["result"].values())[0]

        # Each candle: [time, open, high, low, close, vwap, volume, count]
        candles = [
            {
                "time": c[0],
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[6])
            }
            for c in result[-limit:]
        ]

        return candles

    except Exception:
        return []


def load_cached_candles(coin: str, interval: str):
    path = f"{CACHE_DIR}/{coin}_{interval}.json"
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return None


def save_cached_candles(coin: str, interval: str, candles):
    path = f"{CACHE_DIR}/{coin}_{interval}.json"
    with open(path, "w") as f:
        json.dump(candles, f, indent=4)


def get_candles(coin: str, interval: str = "15m", limit: int = 500):
    """
    Main function your engine will call.
    Uses cache first, then refreshes from Kraken.
    """

    cached = load_cached_candles(coin, interval)

    # If cache exists and is fresh (< 60 seconds old)
    if cached:
        last_ts = cached[-1]["time"]
        now_ts = int(time.time())

        if now_ts - last_ts < 60:
            return cached

    # Fetch fresh candles
    candles = fetch_kraken_ohlc(coin, interval, limit)

    if candles:
        save_cached_candles(coin, interval, candles)

    return candles
