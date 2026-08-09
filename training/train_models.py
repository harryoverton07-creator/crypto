import sys
sys.path.append("/home/harryoverton07/crypto_predictor")


import pandas as pd
import joblib
from feature_pipeline.builder import build_features
from engine.historical import get_candles  # adjust if your path differs
from sklearn.ensemble import RandomForestRegressor

COINS = ["BTC", "ETH", "SOL", "XRP", "ADA"]

def train_single_coin(coin):
    print(f"\n=== Training model for {coin} ===")

    # Load historical candles
    candles = get_candles(coin, "15m", 5000)  # increase if you have more data

    # Build features + label
    df = build_features(candles, include_label=True)

    # Features and target
    X = df.drop(columns=["future_return"])
    y = df["future_return"]

    # Train model
    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        min_samples_split=4,
        random_state=42
    )

    model.fit(X, y)

    # Save model
    save_path = f"models/model_{coin.lower()}.pkl"
    joblib.dump(model, save_path)

    print(f"Model saved: {save_path}")
    print(f"Training samples: {len(df)}")

def train_all():
    for coin in COINS:
        train_single_coin(coin)

if __name__ == "__main__":
    train_all()
