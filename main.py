"""
HTF 4H Alert Bot - FIXED VERSION
================================

Fixes:
1. Uses Binance API for proper 4H candles
2. Corrected Telegram credentials
3. Only checks CLOSED candles
4. Better error handling
5. Shows exactly which candles were compared
"""

import requests
from datetime import datetime
import os
import time

# FIXED: Correct order of credentials
BOT_TOKEN = os.getenv("BOT_TOKEN") or "8263038288:AAGZvc7YTIpnTQyKUV79pMYQBZZnS2ilils"
CHAT_ID = os.getenv("CHAT_ID") or "1118005241"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "LTCUSDT"]
TIMEFRAME = "4h"

def send_telegram(msg):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print(f"✅ Telegram sent: {msg[:50]}...")
        else:
            print(f"❌ Telegram failed: {response.text}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def fetch_binance_4h_candles(symbol, limit=4):
    """
    Fetch proper 4H candles from Binance
    
    Returns last 'limit' CLOSED candles
    """
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": "4h",
        "limit": limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        candles = response.json()
        
        # Convert to readable format
        result = []
        for candle in candles[:-1]:  # Exclude last candle (current, not closed)
            result.append({
                "timestamp": candle[0],
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
                "close_time": candle[6]
            })
        
        return result
    
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return []

def format_time(timestamp_ms):
    """Convert timestamp to readable format"""
    dt = datetime.utcfromtimestamp(timestamp_ms / 1000)
    return dt.strftime('%Y-%m-%d %H:%M UTC')

def check_htf_setup(symbol):
    """
    Check if HTF setup exists for a symbol
    
    Logic: Current closed candle body > both previous candle bodies
    """
    candles = fetch_binance_4h_candles(symbol, limit=4)
    
    if len(candles) < 3:
        print(f"⚠️ {symbol}: Not enough candles (got {len(candles)})")
        return
    
    # Get last 3 CLOSED candles
    prev2 = candles[-3]
    prev1 = candles[-2]
    current = candles[-1]
    
    # Calculate candle bodies
    body_prev2 = abs(prev2["close"] - prev2["open"])
    body_prev1 = abs(prev1["close"] - prev1["open"])
    body_current = abs(current["close"] - current["open"])
    
    # Debug info
    print(f"\n{'='*60}")
    print(f"Checking: {symbol}")
    print(f"{'='*60}")
    print(f"Candle 3 ago: Body={body_prev2:.2f} | {format_time(prev2['timestamp'])}")
    print(f"Candle 2 ago: Body={body_prev1:.2f} | {format_time(prev1['timestamp'])}")
    print(f"Current (closed): Body={body_current:.2f} | {format_time(current['timestamp'])}")
    print(f"\nCondition: {body_current:.2f} > {body_prev1:.2f} AND {body_current:.2f} > {body_prev2:.2f}")
    
    # Check if current body is bigger than BOTH previous
    if body_current > body_prev1 and body_current > body_prev2:
        # Determine direction
        is_green = current["close"] > current["open"]
        direction = "LONG 🟢" if is_green else "SHORT 🔴"
        color = "GREEN" if is_green else "RED"
        
        print(f"✅ SIGNAL FOUND! {direction}")
        
        # Calculate entry details
        entry_price = current["close"]
        
        if is_green:
            stop_loss = current["low"]
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * 0.5)
        else:
            stop_loss = current["high"]
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * 0.5)
        
        # Send Telegram alert
        msg = f"""🚨 <b>HTF 4H SETUP FOUND</b>

<b>Symbol:</b> {symbol}
<b>Direction:</b> {direction}
<b>Candle Color:</b> {color}

<b>Entry Candle Time:</b> {format_time(current['timestamp'])}
<b>Entry Price:</b> ${entry_price:.2f}
<b>Stop Loss:</b> ${stop_loss:.2f}
<b>Take Profit (0.5R):</b> ${take_profit:.2f}

<b>Candle Bodies:</b>
• Current: {body_current:.2f}
• Previous 1: {body_prev1:.2f}
• Previous 2: {body_prev2:.2f}

✅ Current body is BIGGER than both previous candles!

<i>Verify on TradingView: BINANCE:{symbol} 4H chart</i>
"""
        send_telegram(msg)
    else:
        print(f"❌ No signal - body not big enough")
        if body_current <= body_prev1:
            print(f"   Current ({body_current:.2f}) <= Prev1 ({body_prev1:.2f})")
        if body_current <= body_prev2:
            print(f"   Current ({body_current:.2f}) <= Prev2 ({body_prev2:.2f})")

def main():
    print("=" * 60)
    print("HTF 4H ALERT BOT - RUNNING")
    print("=" * 60)
    print(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Checking symbols: {', '.join(SYMBOLS)}")
    print("=" * 60)
    
    alerts_sent = 0
    
    for symbol in SYMBOLS:
        try:
            check_htf_setup(symbol)
            time.sleep(0.5)  # Be nice to Binance API
        except Exception as e:
            print(f"❌ Error checking {symbol}: {e}")
    
    print("\n" + "=" * 60)
    print(f"✅ Scan complete")
    print("=" * 60)

if __name__ == "__main__":
    main()