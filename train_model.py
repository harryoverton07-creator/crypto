import requests
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

PAIR_MAP = {
    "BTC": "XBTUSD",
    "ETH": "ETHUSD",
    "SOL": "SOLUSD",
    "XRP": "XRPUSD",
    "ADA": "ADAUSD",
}

def get_ohlc(coin):
    pair = PAIR_MAP[coin]
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
    r = requests.get(url).json()
    data = list(r["result"].values())[0]

    candles = []
    for c in data:
        candles.append({
            "time": c[0],
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4])
        })
    return candles

def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    diffs = np.diff(closes[-(period + 1):])
    gains = np.where(diffs > 0, diffs, 0.0)
    losses = np.where(diffs < 0, -diffs, 0.0)
    avg_gain = gains.mean()
    avg_loss = losses.mean() if losses.mean() > 0 else 1e-8
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def build_features(candles):
    closes = np.array([c["close"] for c in candles])
    short_ma = closes[-20:].mean()
    long_ma = closes[-60:].mean()
    momentum_10 = closes[-1] - closes[-10]
    volatility_40 = closes[-40:].std()
    ret_5 = (closes[-1] - closes[-5]) / closes[-5] * 100.0
    ret_20 = (closes[-1] - closes[-20]) / closes[-20] * 100.0
    rsi_14 = compute_rsi(closes)
    ma_slope = (closes[-1] - closes[-20]) / 20.0

    return np.array([
        short_ma,
        long_ma,
        momentum_10,
        volatility_40,
        ret_5,
        ret_20,
        rsi_14,
        ma_slope,
    ])

def label(candles):
    closes = np.array([c["close"] for c in candles])
    future = closes[-1] - closes[-5]

    if future > 50:
        return 0
    if future > 10:
        return 1
    if abs(future) <= 10:
        return 2
    if future < -10 and future > -50:
        return 3
    return 4

def build_dataset(coin):
    candles = get_ohlc(coin)
    X = []
    y = []

    for i in range(100, len(candles)):
        window = candles[i-100:i]
        X.append(build_features(window))
        y.append(label(window))

    return np.array(X), np.array(y)

for coin in ["BTC", "ETH", "SOL", "XRP", "ADA"]:
    print(f"\n=== Training {coin} model ===")
    X, y = build_dataset(coin)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model = RandomForestClassifier(n_estimators=200)
    model.fit(X_train, y_train)

    print(f"{coin} accuracy:", model.score(X_test, y_test))
    joblib.dump(model, f"{coin.lower()}_model.pkl")
    print(f"Saved {coin.lower()}_model.pkl")
