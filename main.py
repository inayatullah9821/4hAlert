import requests
from datetime import datetime
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOLS = ["BTC", "ETH", "SOL", "LTC"]
TIMEFRAME = "4h"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

def fetch_ohlcv(symbol):
    url = "https://min-api.cryptocompare.com/data/v2/histohour"
    params = {
        "fsym": symbol,
        "tsym": "USDT",
        "limit": 12,     # 12 hours = 3 x 4H candles
        "aggregate": 4  # aggregate to 4H candles
    }
    res = requests.get(url, params=params, timeout=10).json()
    return res["Data"]["Data"][-3:]

def main():
    for sym in SYMBOLS:
        candles = fetch_ohlcv(sym)

        prev2, prev1, current = candles

        o, c = current["open"], current["close"]
        o1, c1 = prev1["open"], prev1["close"]
        o2, c2 = prev2["open"], prev2["close"]

        body = abs(c - o)
        body1 = abs(c1 - o1)
        body2 = abs(c2 - o2)

        if body > body1 and body > body2:
            direction = "LONG 🟢" if c > o else "SHORT 🔴"
            msg = f"""🚨 HTF SETUP FOUND

Symbol: {sym}/USDT
Timeframe: 4H
Direction: {direction}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Big body candle > previous 2 candles.
"""
            send_telegram(msg)

if __name__ == "__main__":
    main()
