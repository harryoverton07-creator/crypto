import requests

PAIR_MAP = {
    "BTC": "XBTUSD",
    "ETH": "ETHUSD",
    "SOL": "SOLUSD",
    "XRP": "XRPUSD",
    "ADA": "ADAUSD",
}

def get_live_ohlc(coin):
    pair = PAIR_MAP[coin]
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
