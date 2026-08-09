from engine.engine import Engine, Coin
from datetime import datetime
import time
import traceback

def build_engine():
    coins = [
        Coin("BTC"),
        Coin("ETH"),
        Coin("SOL"),
        Coin("XRP"),
        Coin("ADA")
    ]

    starting_balance = 1000  # adjust if needed
    return Engine(coins, starting_balance)


def main():
    engine = build_engine()

    print("\n🚀 Trading engine started")
    print(f"⏱  {datetime.utcnow().isoformat()} UTC\n")

    while True:
        try:
            summary = engine.run_cycle()

            print("────────────────────────────────────────────")
            print(f"Cycle completed at {summary['timestamp']}")
            print(f"Start: £{summary['trading_pot_start']:.2f}")
            print(f"End:   £{summary['trading_pot_end']:.2f}")
            print(f"P/L:   £{summary['profit_loss']:.2f}")
            print(f"Daily Loss: £{summary['daily_loss']:.2f}")
            print("────────────────────────────────────────────\n")

            # 15‑minute cycle (Kraken candle interval)
            time.sleep(900)

        except KeyboardInterrupt:
            print("\n🛑 Manual stop received. Shutting down safely.\n")
            break

        except Exception as e:
            print("\n❌ ERROR during cycle:")
            print(traceback.format_exc())
            print("Continuing engine...\n")
            time.sleep(5)


if __name__ == "__main__":
    main()
