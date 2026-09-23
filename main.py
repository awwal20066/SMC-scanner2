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
  return "SMC Multi-Timeframe (1H & 15M) Scanner is Live!"


def send_smc_alert(symbol, tf_label, setup_type, fvg_top, fvg_bottom):
  message = (
      f"🚨 *SMC ENTRY SETUP DETECTED*\n\n"
      f"• *Pair:* `{symbol}`\n"
      f"• *Timeframe:* `{tf_label}`\n"
      f"• *Type:* `{setup_type}`\n"
      f"• *FVG Zone:* `{fvg_bottom:.5f}` - `{fvg_top:.5f}`\n\n"
      f"Check TradingView to place your limit entry in the FVG zone!"
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


def get_klines(symbol, interval, limit=30):
  url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={interval}&limit={limit}"
  try:
    res = requests.get(url, timeout=5).json()
    if res.get("retCode") == 0 and "list" in res.get("result", {}):
      klines = res["result"]["list"]
      klines.reverse()
      return klines
  except Exception:
    pass
  return None


def analyze_tf(symbol, interval, tf_label, lookback_range):
  klines = get_klines(symbol, interval)
  if not klines or len(klines) < 10:
    return

  highs = [float(k[2]) for k in klines]
  lows = [float(k[3]) for k in klines]
  closes = [float(k[4]) for k in klines]

  # Dynamic structure lookback based on timeframe
  recent_low = min(lows[lookback_range[0] : lookback_range[1]])
  recent_high = max(highs[lookback_range[0] : lookback_range[1]])

  c1_high, c2_high, c3_high = highs[-3], highs[-2], highs[-1]
  c1_low, c2_low, c3_low = lows[-3], lows[-2], lows[-1]

  # 1. Bullish Setup: BOS + FVG
  is_bullish_fvg = c3_low > c1_high
  has_bullish_bos = closes[-1] > recent_high

  if is_bullish_fvg and has_bullish_bos:
    send_smc_alert(
        symbol,
        tf_label,
        "Bullish BOS + FVG",
        fvg_top=c3_low,
        fvg_bottom=c1_high,
    )
    return

  # 2. Bearish Setup: BOS + FVG
  is_bearish_fvg = c3_high < c1_low
  has_bearish_bos = closes[-1] < recent_low

  if is_bearish_fvg and has_bearish_bos:
    send_smc_alert(
        symbol,
        tf_label,
        "Bearish BOS + FVG",
        fvg_top=c1_low,
        fvg_bottom=c3_high,
    )


def analyze_smc_setup(symbol):
  # Scan 1-Hour Timeframe (60 mins)
  analyze_tf(symbol, interval=60, tf_label="1H", lookback_range=(-10, -3))

  # Scan 15-Minute Timeframe (15 mins)
  analyze_tf(symbol, interval=15, tf_label="15M", lookback_range=(-8, -3))


def run_scanner():
  print(
      "🚀 SMC Multi-Timeframe Scanner (1H & 15M BOS + FVG) Started...",
      flush=True,
  )

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
            f"🔍 Scanning ALL {len(usdt_pairs)} USDT pairs on 1H & 15M...",
            flush=True,
        )

        for symbol in usdt_pairs:
          analyze_smc_setup(symbol)
          time.sleep(0.04)

        print("✅ Scan complete. Resting 3 minutes...", flush=True)
    except Exception as e:
      print(f"Scanner error: {e}", flush=True)

    time.sleep(180)


scanner_thread = threading.Thread(target=run_scanner, daemon=True)
scanner_thread.start()

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
  
