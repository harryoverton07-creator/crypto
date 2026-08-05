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

def get_ohlc(pair):
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
    r = requests.get(url, timeout=10).json()
    data = list(r["result"].values())[0]
    candles = []
    for c in data:
        candles.append({
            "time": c[0],
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4]),
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

def build_features(window):
    closes = np.array([c["close"] for c in window])
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

def label_window(window):
    closes = np.array([c["close"] for c in window])
    if len(closes) < 40:
        return 2
    future = (closes[-1] - closes[-20]) / closes[-20] * 100.0
    if future > 2.0:
        return 0
    if future > 0.5:
        return 1
    if abs(future) <= 0.5:
        return 2
    if future < -0.5 and future > -2.0:
        return 3
    return 4

def build_dataset(candles):
    X, y = [], []
    for i in range(200, len(candles)):
        window = candles[i-200:i]
        X.append(build_features(window))
        y.append(label_window(window))
    return np.array(X), np.array(y)

def train_coin_v2(coin):
    print(f"\n=== Training {coin} v2 model ===")
    pair = PAIR_MAP[coin]
    candles = get_ohlc(pair)
    if len(candles) < 400:
        print(f"Not enough data for {coin}, got {len(candles)} candles.")
        return
    X, y = build_dataset(candles)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=123
    )
    model = RandomForestClassifier(
        n_estimators=600,
        max_depth=None,
        random_state=123,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    acc = model.score(X_test, y_test)
    print(f"{coin} v2 accuracy: {acc:.3f}")
    filename = f"{coin.lower()}_model_v2.pkl"
    joblib.dump(model, filename)
    print(f"Saved {filename}")

def main():
    for coin in ["BTC", "ETH", "SOL", "XRP", "ADA"]:
        train_coin_v2(coin)

if __name__ == "__main__":
    main()
