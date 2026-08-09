import os
import json
import joblib
import numpy as np
from datetime import datetime
from engine.historical import get_candles

COINS = ["BTC", "ETH", "SOL", "XRP", "ADA"]

# =========================================================
# MODEL FILES — ABSOLUTE PATHS FOR CRON
# =========================================================

MODEL_DIR = "/home/harryoverton07/crypto_predictor"

MODEL_FILES = {
    "BTC": {
        "v1": f"{MODEL_DIR}/btc_model.pkl",
        "v2": f"{MODEL_DIR}/btc_model_v2.pkl",
        "momentum": f"{MODEL_DIR}/btc_model_momentum.pkl",
        "volatility": f"{MODEL_DIR}/btc_model_volatility.pkl",
        "regime": f"{MODEL_DIR}/btc_model_regime.pkl",
    },
    "ETH": {
        "v1": f"{MODEL_DIR}/eth_model.pkl",
        "v2": f"{MODEL_DIR}/eth_model_v2.pkl",
        "momentum": f"{MODEL_DIR}/eth_model_momentum.pkl",
        "volatility": f"{MODEL_DIR}/eth_model_volatility.pkl",
        "regime": f"{MODEL_DIR}/eth_model_regime.pkl",
    },
    "SOL": {
        "v1": f"{MODEL_DIR}/sol_model.pkl",
        "v2": f"{MODEL_DIR}/sol_model_v2.pkl",
        "momentum": f"{MODEL_DIR}/sol_model_momentum.pkl",
        "volatility": f"{MODEL_DIR}/sol_model_volatility.pkl",
        "regime": f"{MODEL_DIR}/sol_model_regime.pkl",
    },
    "XRP": {
        "v1": f"{MODEL_DIR}/xrp_model.pkl",
        "v2": f"{MODEL_DIR}/xrp_model_v2.pkl",
        "momentum": f"{MODEL_DIR}/xrp_model_momentum.pkl",
        "volatility": f"{MODEL_DIR}/xrp_model_volatility.pkl",
        "regime": f"{MODEL_DIR}/xrp_model_regime.pkl",
    },
    "ADA": {
        "v1": f"{MODEL_DIR}/ada_model.pkl",
        "v2": f"{MODEL_DIR}/ada_model_v2.pkl",
        "momentum": f"{MODEL_DIR}/ada_model_momentum.pkl",
        "volatility": f"{MODEL_DIR}/ada_model_volatility.pkl",
        "regime": f"{MODEL_DIR}/ada_model_regime.pkl",
    },
}


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


def load_models_for_coin(coin):
    files = MODEL_FILES[coin]
    models = {}
    for key, fname in files.items():
        if not os.path.exists(fname):
            raise FileNotFoundError(f"Missing model file for {coin}: {fname}")
        models[key] = joblib.load(fname)
    return models


import joblib
from feature_pipeline.builder import build_features

def get_ensemble_signal(coin, candles):

    # 1. Build features (no label in live mode)
    features = build_features(candles, include_label=False)

    # 2. Load the correct model for this coin
    model_path = f"models/model_{coin.lower()}.pkl"
    model = joblib.load(model_path)

    # 3. Predict the future return using the latest row
    latest_row = features.tail(1)
    prediction = model.predict(latest_row)[0]

    # 4. Convert prediction → BUY / SELL / HOLD
    if prediction > 0.002:
        ml_signal = "BUY"
    elif prediction < -0.002:
        ml_signal = "SELL"
    else:
        ml_signal = "HOLD"

    # 5. Confidence = absolute size of prediction
    confidence = abs(prediction)

    # 6. Return the signal + confidence + placeholders
    return ml_signal, confidence, 0, 0, "normal"

class Coin:
    def __init__(self, name):
        self.name = name
        self.latest_prob = None
        self.latest_signal = None
        self.latest_confidence = None
        self.latest_vol = None
        self.latest_risk_factor = None
        self.latest_regime = None


class Engine:
    def __init__(self, vault):
        self.vault = vault
        self.coins = [Coin(name) for name in COINS]

        self.trading_pot = self.vault.balance
    
    def run_cycle(self):
    # starting pot
        trading_pot_start = self.vault.balance

        positions = {}
        allocations = {}
        btc_regime = None

    # build positions
            # build positions into Coin objects
        for coin in self.coins:
            

            candles = get_candles(coin.name, "15m", 500)

            ml_signal, confidence, vol, risk_factor, regime = get_ensemble_signal(coin.name, candles)

            coin.latest_signal = ml_signal
            coin.latest_confidence = confidence
            coin.latest_risk_factor = risk_factor
            coin.latest_regime = regime
            coin.latest_prob = confidence  # or whatever metric you use
        positions[coin.name] = {
            "signal": ml_signal,
            "confidence": confidence,
            "volatility": vol,
            "risk_factor": risk_factor,
            "regime": regime
        }

    # load coins + trading pot
        coins = self.coins
        trading_pot = self.trading_pot

    # dynamic allocation using Coin objects
        allocations = variable_cap_allocation(self.coins, self.trading_pot)

    # === NEW ML-BASED TRADING LOGIC ===

        profit_loss = 0.0
  
        for coin in self.coins:

    # BUY → increase profit based on allocation and confidence
            if coin.latest_signal == "BUY":
                profit_loss += allocations.get(coin.name, 0) * coin.latest_confidence

    # SELL → decrease profit based on allocation and confidence
            elif coin.latest_signal == "SELL":
                profit_loss -= allocations.get(coin.name, 0) * coin.latest_confidence

    # HOLD → no change
            else:
                pass

# update trading pot
        trading_pot_end = trading_pot_start + profit_loss


    # skim 10% of profit to vault if positive
        skimmed = 0.0
        if profit_loss > 0:
            skimmed = profit_loss * 0.1
            self.vault.vault_value += skimmed
            trading_pot_end -= skimmed

    # update vault balance
        self.vault.balance = trading_pot_end

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "trading_pot_start": trading_pot_start,
            "trading_pot_end": trading_pot_end,
            "profit_loss": profit_loss,
            "skimmed": skimmed,
            "positions": {coin.name: {"signal": coin.latest_signal} for coin in self.coins},
            "allocations": allocations,
            "btc_regime": btc_regime,
        }

# ⭐ ADD VERSION STAMP HERE 
        summary["version"] = datetime.utcnow().isoformat()

# ⭐ WRITE DASHBOARD BEFORE RETURN
        os.makedirs("dashboards", exist_ok=True)
        with open(os.path.join("dashboards", "dashboard.json"), "w") as f:
            json.dump(summary, f, indent=2)

# ⭐ WRITE HISTORY BEFORE RETURN
        os.makedirs("history", exist_ok=True)
        history_path = os.path.join("history", "portfolio_history.json")
        entry = {
            "timestamp": summary["timestamp"],
            "trading_pot": trading_pot_end,
            "vault": self.vault.balance,
            "profit_loss": profit_loss,
        }
# append entry to history file here…

# ⭐ NOW return summary
        return summary
       

        # write dashboard summary
        os.makedirs("dashboards", exist_ok=True)
        with open(os.path.join("dashboards", "dashboard.json"), "w") as f:
            json.dump(summary, f, indent=2)

        # write equity curve history
        os.makedirs("history", exist_ok=True)
        history_path = os.path.join("history", "portfolio_history.json")
        entry = {
            "timestamp": summary["timestamp"],
            "trading_pot": summary["trading_pot_end"],
        }
        if os.path.exists(history_path):
            with open(history_path, "r") as f:
                data = json.load(f)
        else:
            data = []
        data.append(entry)
        with open(history_path, "w") as f:
            json.dump(data, f, indent=2)

        # write per-coin P&L
        coin_pnl_path = os.path.join("history", "coin_pnl.json")
        if os.path.exists(coin_pnl_path):
            with open(coin_pnl_path, "r") as f:
                coin_pnl = json.load(f)
        else:
            coin_pnl = {c: 0 for c in COINS}

        for coin in COINS:
            sig = positions[coin]["signal"]
            if sig == "BUY":
                coin_pnl[coin] += profit_loss * allocations[coin]

        with open(coin_pnl_path, "w") as f:
            json.dump(coin_pnl, f, indent=2)

        return summary
def variable_cap_allocation(coins, shared_balance, cap=0.30):
    active = [c for c in coins if c.latest_prob and c.latest_prob > 0.10]

    if not active:
        return {}

    total_conf = sum(c.latest_prob for c in active)
    raw_weights = {c.name: c.latest_prob / total_conf for c in active}

    capped = {}
    leftover = 1.0

    for name, weight in raw_weights.items():
        allocation = min(weight, cap)
        capped[name] = allocation
        leftover -= allocation

    uncapped_total = sum(raw_weights[name] for name in raw_weights if raw_weights[name] < cap)

    if uncapped_total > 0:
        for name in capped:
            if raw_weights[name] < cap:
                capped[name] += leftover * (raw_weights[name] / uncapped_total)

    final_allocations = {name: shared_balance * pct for name, pct in capped.items()}
    return final_allocations
