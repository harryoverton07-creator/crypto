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


def get_ensemble_signal(coin, candles):
    models = load_models_for_coin(coin)
    X = build_features(candles).reshape(1, -1)

    # sanity check: all models must match feature count
    for name, m in models.items():
        if getattr(m, "n_features_in_", X.shape[1]) != X.shape[1]:
            raise ValueError(
                f"{coin} model feature mismatch: model expects {m.n_features_in_}, "
                f"engine provides {X.shape[1]}"
            )

    # base + v2 + momentum as main signal ensemble
    v1_pred = int(models["v1"].predict(X)[0])
    v2_pred = int(models["v2"].predict(X)[0])
    mom_pred = int(models["momentum"].predict(X)[0])

    # volatility + regime as context
    vol_pred = int(models["volatility"].predict(X)[0])
    regime_pred = int(models["regime"].predict(X)[0])

    # simple majority vote for direction
    votes = [v1_pred, v2_pred, mom_pred]
    direction = max(set(votes), key=votes.count)

    # map class to signal
    if direction in [0, 1]:  # up-ish
        signal = "BUY"
    elif direction in [3, 4]:  # down-ish
        signal = "SELL"
    else:
        signal = "HOLD"

    # crude confidence: fraction of agreeing models
    confidence = votes.count(direction) / len(votes)

    # volatility regime mapping (example)
    if vol_pred <= 1:
        regime = "LOW_VOL"
    elif vol_pred == 2:
        regime = "MED_VOL"
    else:
        regime = "HIGH_VOL"

    # risk factor from regime
    if regime == "LOW_VOL":
        risk_factor = 1.0
    elif regime == "MED_VOL":
        risk_factor = 0.7
    else:
        risk_factor = 0.4

    return signal, confidence, vol_pred, risk_factor, regime
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

    # simple P&L simulation
        profit_loss = 0.0
        for coin, pos in positions.items():
            if pos["signal"] == "BUY":
                profit_loss += 1.5 * allocations[coin]
            elif pos["signal"] == "SELL":
                profit_loss -= 1.0 * allocations[coin]

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
