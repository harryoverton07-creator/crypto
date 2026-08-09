import os
import json
from datetime import datetime
import joblib
from feature_pipeline.builder import build_features
from engine.historical import get_candles
import subprocess

def auto_git_push():
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto update at {datetime.utcnow().isoformat()}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Auto Git push successful.")
    except Exception as e:
        print("❌ Git push failed:", e)


MODEL_FILES = {
    # keep your existing mapping here if you use load_models_for_coin
}


def get_ensemble_signal(coin, candles):
    # 1. Build features (no label in live mode)
    features = build_features(candles, include_label=False)

    # 2. Load the correct model for this coin
    model_path = f"models/model_{coin.lower()}.pkl"
    model = joblib.load(model_path)

    # 3. Predict the future return using the latest row
    latest_row = features.tail(1)
    prediction = model.predict(latest_row)[0]

    # === FIXED SIGNAL LOGIC ===

    # raw confidence = absolute prediction size
    raw_conf = float(abs(prediction))

    # scale raw ML confidence
    scaled_conf = raw_conf * 1000

    # regime placeholder (upgrade later if you want)
    regime = "normal"

    # regime adjustment
    if regime == "bullish":
        scaled_conf *= 1.15
    elif regime == "bearish":
        scaled_conf *= 0.85

    # clamp confidence between 0 and 1
    scaled_conf = max(0.0, min(1.0, scaled_conf))

    # volatility placeholder (you can compute real vol from candles later)
    vol = 0.0

    # volatility kill‑switch
    if vol > 0.03:  # 3% candle volatility
        ml_signal = "HOLD"
        scaled_conf = 0.0
    else:
        # determine signal
        if scaled_conf > 0.55:
            ml_signal = "BUY"
        elif scaled_conf < 0.45:
            ml_signal = "SELL"
        else:
            ml_signal = "HOLD"

    confidence = scaled_conf
    risk_factor = 0.0  # placeholder

    return ml_signal, confidence, vol, risk_factor, regime


class Coin:
    def __init__(self, name):
        self.name = name
        self.latest_prob = None
        self.latest_signal = None
        self.latest_confidence = None
        self.latest_vol = None
        self.latest_risk_factor = None
        self.latest_regime = None


class Vault:
    def __init__(self, starting_balance: float):
        self.balance = starting_balance
        self.daily_loss = 0.0
        self.last_reset_date = datetime.utcnow().date()

    def reset_daily_loss_if_needed(self):
        today = datetime.utcnow().date()
        if today != self.last_reset_date:
            self.daily_loss = 0.0
            self.last_reset_date = today


class Engine:
    def __init__(self, coins, starting_balance: float):
        self.coins = coins
        self.vault = Vault(starting_balance)
        self.starting_balance = starting_balance

    def variable_cap_allocation(self, coins, trading_pot):
        active = [c for c in coins if c.latest_prob and c.latest_prob > 0.10]

        if not active:
            return {c.name: trading_pot / len(coins) for c in coins}

        total_conf = sum(c.latest_confidence for c in active)

        allocations = {}
        for coin in coins:
            if coin in active and total_conf > 0:
                allocations[coin.name] = (coin.latest_confidence / total_conf) * trading_pot
            else:
                allocations[coin.name] = 0.0

        return allocations

    def run_cycle(self):

        # reset daily loss if new day
        self.vault.reset_daily_loss_if_needed()

        trading_pot_start = self.vault.balance
        positions = {}

        # build positions + signals
        for coin in self.coins:
            candles = get_candles(coin.name, "15m", 500)

            ml_signal, confidence, vol, risk_factor, regime = get_ensemble_signal(coin.name, candles)

            coin.latest_signal = ml_signal
            coin.latest_confidence = confidence
            coin.latest_risk_factor = risk_factor
            coin.latest_regime = regime
            coin.latest_prob = confidence
            coin.latest_vol = vol

            positions[coin.name] = {
                "signal": ml_signal,
                "confidence": confidence,
                "volatility": vol,
                "risk_factor": risk_factor,
                "regime": regime
            }

        # dynamic allocation
        allocations = self.variable_cap_allocation(self.coins, trading_pot_start)

        profit_loss = 0.0

        # confidence‑weighted sizing + max‑loss cap
        max_cycle_loss = trading_pot_start * 0.02  # 2% per cycle

        for coin in self.coins:
            base_alloc = allocations.get(coin.name, 0.0)

            # confidence‑weighted position size
            trade_size = base_alloc * (coin.latest_confidence ** 2)

            if coin.latest_signal == "BUY":
                profit_loss += trade_size
            elif coin.latest_signal == "SELL":
                profit_loss -= trade_size

            # cap cycle loss
            if profit_loss < -max_cycle_loss:
                profit_loss = -max_cycle_loss
                break

        trading_pot_end = trading_pot_start + profit_loss

        # update vault + daily loss
        self.vault.balance = trading_pot_end
        if profit_loss < 0:
            self.vault.daily_loss += abs(profit_loss)

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "trading_pot_start": trading_pot_start,
            "trading_pot_end": trading_pot_end,
            "profit_loss": profit_loss,
            "skimmed": 0.0,
            "positions": positions,
            "allocations": allocations,
            "btc_regime": None,
            "version": datetime.utcnow().isoformat(),
            "daily_loss": self.vault.daily_loss,
        }

        # ============================
# NEW DASHBOARD + HISTORY EXPORT
# ============================

# ---- SECTION 1: ALL TIME ----
        total_vault_value = self.vault.balance
        total_profit_loss = self.vault.balance - self.starting_balance
        percent_change = (total_profit_loss / self.starting_balance) * 100
        total_portfolio_value = trading_pot_end + total_vault_value

# ---- SECTION 2: LAST TRADE ----
        last_trade = {
            coin.name: {
                "signal": coin.latest_signal,
                "confidence": coin.latest_confidence,
                "allocation": allocations.get(coin.name, 0),
                "trade_size": allocations.get(coin.name, 0) * (coin.latest_confidence ** 2),
                "pnl": 0.0,
                "skimmed": 0.0
            }
            for coin in self.coins
        }
  
        dashboard = {
            "timestamp": datetime.utcnow().isoformat(),
   
            "all_time": {
                "total_profit_loss": total_profit_loss,
                "percent_change": percent_change,
                "total_portfolio_value": total_portfolio_value,
                "total_vault_value": total_vault_value
            },

            "last_trade": last_trade
        }

# ---- WRITE DASHBOARD ----
        with open("dashboard.json", "w") as f:
            json.dump(dashboard, f, indent=4)

# ---- WRITE HISTORY ----
        history_entry = {
            "timestamp": dashboard["timestamp"],
            "trading_pot": trading_pot_end,
            "profit_loss": profit_loss,
            "daily_loss": self.vault.daily_loss
        }
  
        with open("portfolio_history.json", "a") as f:
            json.dump(history_entry, f)
            f.write("\n")

        import subprocess

        try:
            auto_git_push() 
        except Exception as e:
            print("❌ Git push failed:", e)
        finally:
            return summary

        
