import joblib

files = [
    "btc_model.pkl",
    "btc_model_v2.pkl",
    "btc_model_momentum.pkl",
    "btc_model_volatility.pkl",
    "btc_model_regime.pkl",
]

for f in files:
    try:
        m = joblib.load(f)
        print(f, "n_features_in_ =", getattr(m, "n_features_in_", "NO ATTRIBUTE"))
    except Exception as e:
        print(f, "ERROR:", e)
