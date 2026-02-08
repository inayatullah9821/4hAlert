"""
HTF 4H Alert Bot - GITHUB ACTIONS COMPATIBLE
============================================

Uses alternative APIs that work from GitHub Actions/cloud servers
Since Binance blocks cloud IPs, we use proxied or alternative data sources
"""

import requests
from datetime import datetime, timedelta
import os
import time

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
            return True
        else:
            print(f"❌ Telegram failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def fetch_candles_coingecko(symbol, limit=4):
    """
    Fetch candles from CoinGecko (works from GitHub Actions)
    Free tier: 10-50 calls/min
    """
    
    # Map symbols to CoinGecko IDs
    symbol_map = {
        "BTCUSDT": "bitcoin",
        "ETHUSDT": "ethereum",
        "SOLUSDT": "solana",
        "LTCUSDT": "litecoin",
        "BNBUSDT": "binancecoin",
        "ADAUSDT": "cardano",
        "DOGEUSDT": "dogecoin",
        "XRPUSDT": "ripple"
    }
    
    coin_id = symbol_map.get(symbol)
    if not coin_id:
        print(f"⚠️ {symbol} not supported by CoinGecko")
        return []
    
    # CoinGecko returns hourly data, we'll aggregate to 4H
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    
    # Get last 24 hours of hourly data (6 x 4H candles)
    params = {
        "vs_currency": "usd",
        "days": "2",  # Last 2 days to be safe
        "interval": "hourly"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        prices = data.get("prices", [])
        if not prices:
            return []
        
        # Aggregate hourly to 4H candles
        candles = aggregate_to_4h(prices)
        
        # Return last N closed candles
        return candles[-(limit+1):-1]  # Exclude current candle
        
    except Exception as e:
        print(f"❌ CoinGecko error for {symbol}: {e}")
        return []

def aggregate_to_4h(hourly_prices):
    """
    Aggregate hourly price data to 4H candles
    
    Args:
        hourly_prices: List of [timestamp_ms, price]
    
    Returns:
        List of candle dicts
    """
    if not hourly_prices:
        return []
    
    candles = []
    current_candle = None
    
    for timestamp_ms, price in hourly_prices:
        dt = datetime.utcfromtimestamp(timestamp_ms / 1000)
        
        # Determine which 4H period this belongs to
        hour = dt.hour
        candle_hour = (hour // 4) * 4  # 0, 4, 8, 12, 16, 20
        candle_start = dt.replace(hour=candle_hour, minute=0, second=0, microsecond=0)
        candle_timestamp = int(candle_start.timestamp() * 1000)
        
        # Start new candle or update current
        if current_candle is None or current_candle["timestamp"] != candle_timestamp:
            if current_candle is not None:
                candles.append(current_candle)
            
            current_candle = {
                "timestamp": candle_timestamp,
                "open": price,
                "high": price,
                "low": price,
                "close": price
            }
        else:
            # Update current candle
            current_candle["high"] = max(current_candle["high"], price)
            current_candle["low"] = min(current_candle["low"], price)
            current_candle["close"] = price
    
    # Add last candle
    if current_candle:
        candles.append(current_candle)
    
    return candles

def fetch_candles_binance_proxy(symbol, limit=4):
    """
    Try to fetch from Binance via public proxy/mirror
    """
    # Try binance vision (historical data)
    # Or use a public API aggregator
    
    urls_to_try = [
        f"https://api.binance.com/api/v3/klines",
        f"https://data.binance.com/api/v3/klines",
        f"https://www.binance.com/api/v3/klines",
    ]
    
    params = {
        "symbol": symbol,
        "interval": "4h",
        "limit": limit
    }
    
    for url in urls_to_try:
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # If blocked (451), try next
            if response.status_code == 451:
                continue
                
            response.raise_for_status()
            candles_raw = response.json()
            
            # Convert to our format
            candles = []
            for candle in candles_raw[:-1]:  # Exclude current
                candles.append({
                    "timestamp": candle[0],
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4])
                })
            
            print(f"✅ Fetched from {url}")
            return candles
            
        except Exception as e:
            continue
    
    return []

def fetch_4h_candles(symbol, limit=4):
    """
    Smart fetch: Try multiple sources
    1. Binance direct (works locally)
    2. Binance mirrors (might work on GitHub)
    3. CoinGecko (always works)
    """
    
    print(f"Fetching {symbol}...")
    
    # Try Binance first
    candles = fetch_candles_binance_proxy(symbol, limit)
    if candles:
        return candles
    
    print(f"⚠️ Binance blocked, using CoinGecko for {symbol}...")
    
    # Fallback to CoinGecko
    candles = fetch_candles_coingecko(symbol, limit)
    if candles:
        return candles
    
    print(f"❌ All sources failed for {symbol}")
    return []

def format_time(timestamp_ms):
    """Convert timestamp to readable format"""
    dt = datetime.utcfromtimestamp(timestamp_ms / 1000)
    return dt.strftime('%Y-%m-%d %H:%M UTC')

def check_htf_setup(symbol):
    """Check if HTF setup exists"""
    
    candles = fetch_4h_candles(symbol, limit=4)
    
    if len(candles) < 3:
        print(f"⚠️ {symbol}: Not enough candles (got {len(candles)})")
        return
    
    # Get last 3 CLOSED candles
    prev2 = candles[-3]
    prev1 = candles[-2]
    current = candles[-1]
    
    # Calculate bodies
    body_prev2 = abs(prev2["close"] - prev2["open"])
    body_prev1 = abs(prev1["close"] - prev1["open"])
    body_current = abs(current["close"] - current["open"])
    
    # Debug
    print(f"\n{'='*60}")
    print(f"Checking: {symbol}")
    print(f"{'='*60}")
    print(f"Candle 3 ago: Body={body_prev2:.2f} | {format_time(prev2['timestamp'])}")
    print(f"Candle 2 ago: Body={body_prev1:.2f} | {format_time(prev1['timestamp'])}")
    print(f"Current (closed): Body={body_current:.2f} | {format_time(current['timestamp'])}")
    print(f"\nCondition: {body_current:.2f} > {body_prev1:.2f} AND {body_current:.2f} > {body_prev2:.2f}")
    
    # Check setup
    if body_current > body_prev1 and body_current > body_prev2:
        is_green = current["close"] > current["open"]
        direction = "LONG 🟢" if is_green else "SHORT 🔴"
        color = "GREEN" if is_green else "RED"
        
        print(f"✅ SIGNAL FOUND! {direction}")
        
        # Calculate levels
        entry_price = current["close"]
        
        if is_green:
            stop_loss = current["low"]
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * 0.5)
        else:
            stop_loss = current["high"]
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * 0.5)
        
        # Send alert
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
        print(f"❌ No signal")

def main():
    print("=" * 60)
    print("HTF 4H ALERT BOT - GITHUB ACTIONS COMPATIBLE")
    print("=" * 60)
    print(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print("=" * 60)
    
    for symbol in SYMBOLS:
        try:
            check_htf_setup(symbol)
            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"❌ Error checking {symbol}: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Scan complete")
    print("=" * 60)

if __name__ == "__main__":
    main()