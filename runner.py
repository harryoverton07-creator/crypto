from engine.engine import Engine
from shared_vault import Vault
from live_data import get_live_ohlc

def main():
    vault = Vault()
    vault.load()

    for coin in ["BTC", "ETH", "SOL", "XRP", "ADA"]:
        vault.data[coin] = get_live_ohlc(coin)

    engine = Engine(vault)
    summary = engine.run_cycle()

    print(summary)   # ← ADD THIS

    vault.save()

if __name__ == "__main__":
    main()
