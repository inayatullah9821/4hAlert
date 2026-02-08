import ccxt
import requests
from datetime import datetime
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "LTC/USDT"]
TIMEFRAME = "4h"

exchange = ccxt.bybit({'enableRateLimit': True})

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

def main():
    alerts = []

    for symbol in SYMBOLS:
        ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=3)

        prev2 = ohlcv[-3]
        prev1 = ohlcv[-2]
        current = ohlcv[-1]  # last closed 4H candle

        o, c = current[1], current[4]
        o1, c1 = prev1[1], prev1[4]
        o2, c2 = prev2[1], prev2[4]

        body = abs(c - o)
        body1 = abs(c1 - o1)
        body2 = abs(c2 - o2)

        if body > body1 and body > body2:
            direction = "LONG 🟢" if c > o else "SHORT 🔴"
            msg = f"""🚨 HTF SETUP FOUND

Symbol: {symbol}
Timeframe: 4H
Direction: {direction}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Big body candle > previous 2 candles.
"""
            send_telegram(msg)
            alerts.append(symbol)

    print("Alerts sent for:", alerts)

if __name__ == "__main__":
    main()
