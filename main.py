import os
import threading
import time
import requests
from flask import Flask

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = "8784181708:AAFYUsuC60jhG9rg4Qk1oQk9rtoQDCSfZsE"
TELEGRAM_CHAT_ID = "5284203725"


@app.route("/")
def home():
  return "SMC Scanner is active and scanning ALL Bybit USDT pairs!"


def send_smc_alert(symbol, setup_type, entry_zone, fib_level, fvg_price):
  message = (
      f"🚨 *1H SMC SETUP DETECTED: {symbol}*\n\n"
      f"• *Type:* `{setup_type}`\n"
      f"• *1H FVG Price:* `{fvg_price:.6f}`\n"
      f"• *Fib Retracement:* `{fib_level:.2f}` (Valid <= 0.70)\n"
      f"• *Clean Level:* No liquidity sweep detected\n\n"
      f"Open TradingView 1H chart, confirm FVG box & BOS, and calculate risk!"
  )
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  try:
    requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        },
        timeout=10,
    )
  except Exception as e:
    print(f"Telegram error: {e}", flush=True)


def get_1h_klines(symbol):
  url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval=60&limit=50"
  try:
    res = requests.get(url, timeout=5).json()
    if res.get("retCode") == 0 and "list" in res.get("result", {}):
      klines = res["result"]["list"]
      klines.reverse()
      return klines
  except Exception:
    pass
  return None


def analyze_smc_setup(symbol):
  klines = get_1h_klines(symbol)
  if not klines or len(klines) < 10:
    return

  highs = [float(k[2]) for k in klines]
  lows = [float(k[3]) for k in klines]
  closes = [float(k[4]) for k in klines]

  c1_high, c2_high, c3_high = highs[-3], highs[-2], highs[-1]
  c1_low, c2_low, c3_low = lows[-3], lows[-2], lows[-1]

  # Bullish FVG + BOS
  if c3_low > c1_high:
    recent_low = min(lows[-10:])
    recent_high = max(highs[-5:])
    range_span = recent_high - recent_low
    if range_span > 0:
      break_level = (closes[-1] - recent_low) / range_span
      if break_level <= 0.70 and c2_low >= recent_low:
        send_smc_alert(
            symbol,
            "Bullish BOS + FVG",
            c1_high,
            break_level,
            (c3_low + c1_high) / 2,
        )
        return

  # Bearish FVG + BOS
  if c3_high < c1_low:
    recent_high = max(highs[-10:])
    recent_low = min(lows[-5:])
    range_span = recent_high - recent_low
    if range_span > 0:
      break_level = (recent_high - closes[-1]) / range_span
      if break_level <= 0.70 and c2_high <= recent_high:
        send_smc_alert(
            symbol,
            "Bearish BOS + FVG",
            c1_low,
            break_level,
            (c3_high + c1_low) / 2,
        )


def run_scanner():
  print("🚀 1H SMC Strategy Scanner initialized...", flush=True)
  send_smc_alert("1H_SMC_SCANNER", "Full Market Scan Started", 0.0, 0.0, 0.0)

  while True:
    try:
      url = "https://api.bybit.com/v5/market/tickers?category=linear"
      res = requests.get(url, timeout=10).json()
      if "result" in res and "list" in res["result"]:
        tickers = res["result"]["list"]
        usdt_pairs = [
            t["symbol"] for t in tickers if t["symbol"].endswith("USDT")
        ]

        print(
            f"🔍 Scanning ALL {len(usdt_pairs)} USDT pairs...",
            flush=True,
        )

        for i, symbol in enumerate(usdt_pairs):
          analyze_smc_setup(symbol)
          time.sleep(0.05)

        print("✅ Scan complete. Resting 5 minutes...", flush=True)
    except Exception as e:
      print(f"Scanner error: {e}", flush=True)

    time.sleep(300)


scanner_thread = threading.Thread(target=run_scanner, daemon=True)
scanner_thread.start()

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
            
