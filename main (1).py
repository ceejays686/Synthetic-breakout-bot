import time
import json
import threading
import websocket
import requests
import logging
from datetime import datetime

# === Config ===
TELEGRAM_TOKEN = '8133734674:AAHIqhFRGfW7-hWwlNWTN264saqJZhxdgA8'
TELEGRAM_CHAT_ID = '@CeejaySignal_bot'
import os
DERIV_API_TOKEN = os.getenv('DERIV_API_TOKEN')

ASSETS = {
    'R_25': {'symbol': 'R_25', 'tp': 20},
    'R_50': {'symbol': 'R_50', 'tp': 40},
    'R_75': {'symbol': 'R_75', 'tp': 60},
    'R_100': {'symbol': 'R_100', 'tp': 50}
}

lot_size = 0.01
win_count = 0
trade_memory = {}
candle_history = {k: [] for k in ASSETS}

# === Logging Setup ===
logging.basicConfig(filename='logs.txt', level=logging.INFO,
                    format='%(asctime)s - %(message)s')

# === Helpers ===
def log(msg):
    logging.info(msg)
    print(msg)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def adjust_lot(win):
    global lot_size, win_count
    if win:
        win_count += 1
        if win_count >= 3:
            lot_size = round(lot_size * 1.5, 2)
            win_count = 0
    else:
        lot_size = round(max(lot_size / 2, 0.01), 2)
        win_count = 0

def detect_breakout(symbol, candles):
    if len(candles) < 2:
        return None
    prev, curr = candles[-2], candles[-1]
    if curr['close'] > prev['high']:
        return 'buy'
    elif curr['close'] < prev['low']:
        return 'sell'
    return None

def simulate_trade(symbol, direction, tp, sl, entry_price):
    result = "win" if direction == "buy" else "loss"
    adjust_lot(result == "win")
    msg = f"Simulated {direction.upper()} | {symbol} | Entry: {entry_price} | TP: {tp} | SL: {sl} | Result: {result.upper()} | New lot size: {lot_size}"
    log(msg)
    send_telegram(msg)

def on_message(ws, message):
    data = json.loads(message)
    if "candles" in data:
        symbol = data["echo_req"]["ticks_history"]
        candles = data["candles"]
        candle_history[symbol] = candles
        direction = detect_breakout(symbol, candles)
        if direction:
            entry = candles[-1]['close']
            sl = candles[-1]['low'] if direction == 'buy' else candles[-1]['high']
            tp = ASSETS[symbol]['tp']
            simulate_trade(symbol, direction, tp, sl, entry)

def on_open(ws):
    ws.send(json.dumps({"authorize": DERIV_API_TOKEN}))
    for asset in ASSETS:
        ws.send(json.dumps({
            "ticks_history": ASSETS[asset]["symbol"],
            "adjust_start_time": 1,
            "count": 20,
            "granularity": 900,
            "style": "candles",
            "subscribe": 1
        }))

def on_error(ws, error):
    log(f"WebSocket Error: {error}")

def connect():
    ws = websocket.WebSocketApp(
        "wss://ws.derivws.com/websockets/v3?app_id=1089",
        on_message=on_message,
        on_open=on_open,
        on_error=on_error
    )
    ws.run_forever()

# === Run Bot ===
if __name__ == "__main__":
    log("Bot starting...")
    send_telegram("Bot Started: Watching for breakout candles.")
    threading.Thread(target=connect).start()
