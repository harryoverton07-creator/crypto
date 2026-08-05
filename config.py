# ============================
# CONFIG.PY — CORE SETTINGS
# ============================

# Coins the engine trades
COINS = ["BTC", "ETH", "SOL", "XRP", "ADA"]

# Futures pairs for each coin
FUTURES = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT"
}

# File paths
VAULT_PATH = "vaults/vault.json"
DASHBOARD_PATH = "dashboards/dashboard.json"
PORTFOLIO_HISTORY_PATH = "history/portfolio_history.json"
ALLOCATION_PATH = "dashboards/allocation.json"

# Model settings
MODEL = {
    "trend_window": 48,
    "reversal_window": 12,
    "confidence_threshold": 0.65
}

# Hedging settings
HEDGING = {
    "max_position_size": 0.25,   # 25% of trading pot per asset
    "hedge_ratio": 0.35          # 35% hedge on strong down signals
}
