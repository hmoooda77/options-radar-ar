#!/usr/bin/env python3
"""Bitcoin Paper-Trading Dashboard HTTP Server.
STANDARD LIBRARY ONLY – PAPER MODE ONLY.
"""
import http.server
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone

PORT = int(os.environ.get("PORT", 10000))
BINANCE_TICK = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
BINANCE_KLINE = ("https://api.binance.com/api/v3/klines"
                 "?symbol=BTCUSDT&interval=1m&limit=25")
TIMEOUT = 8
INIT_CASH = 10.0
MAX_CASH_PCT = 0.90
FEE_PCT = 0.001


class SimState:
    """In-memory paper-trading state."""

    def __init__(self):
        self.lock = threading.Lock()
        self.cash = INIT_CASH
        self.btc = 0.0
        self.trades = []
        self.sma5_history = deque(maxlen=25)
        self.sma20_history = deque(maxlen=25)
        self.prev_sma5 = None
        self.prev_sma20 = None

    def _sma(self, data, window):
        return round(sum(data[-window:]) / window, 2) if len(data) >= window else None

    def process_candle(self, close_price):
        with self.lock:
            self.sma5_history.append(close_price)
            sma5 = self._sma(self.sma5_history, 5)
            self.sma20_history.append(close_price)
            sma20 = self._sma(self.sma20_history, 20)
            equity = round(self.cash + self.btc * close_price, 4)
            result = {"sma5": sma5, "sma20": sma20, "equity": equity,
                      "cash": round(self.cash, 4), "btc": round(self.btc, 8)}
            # BUY: upward crossover (sma5 crosses above sma20) while flat
            if (sma5 is not None and sma20 is not None
                    and self.prev_sma5 is not None and self.prev_sma20 is not None
                    and self.prev_sma5 - self.prev_sma20 >= 0
                    and sma5 - sma20 > 0
                    and self.btc == 0):
                spend = self.cash * MAX_CASH_PCT
                fee = spend * FEE_PCT
                actual = spend - fee
                qty = round(actual / close_price, 8)
                self.btc = qty
                self.cash -= spend
                self.trades.append({"side": "BUY", "qty": qty,
                                    "price": close_price,
                                    "time": datetime.now(timezone.utc).isoformat()})
                result["signal"] = "BUY"
            # SELL: downward crossover (sma5 crosses below sma20) while holding
            elif (sma5 is not None and sma20 is not None
                  and self.prev_sma5 is not None and self.prev_sma20 is not None
                  and self.prev_sma5 - self.prev_sma20 >= 0
                  and sma5 - sma20 > 0
                  and self.btc > 0):
                fee = self.btc * close_price * FEE_PCT
                proceeds = self.btc * close_price - fee
                self.cash += proceeds
                self.btc = 0.0
                self.trades.append({"side": "SELL",
                                    "qty": round(self.btc, 8),
                                    "price": close_price,
                                    "time": datetime.now(timezone.utc).isoformat()})
                result["signal"] = "SELL"
            self.prev_sma5 = sma5
            self.prev_sma20 = sma20
            return result


state = SimState()


def fetch_json(url):
    """Fetch JSON from URL with timeout, returns None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def get_feed_data():
    """Fetch Binance ticker and klines. Returns (price, closes) or None."""
    price_data = fetch_json(BINANCE_TICK)
    if not price_data:
        return None
    price = float(price_data["price"])
    kline_data = fetch_json(BINANCE_KLINE)
    if not kline_data:
        return None
    # Binance klines: [time, open, high, low, close, ...]
    closes = []
    for k in kline_data:
        closes.append(float(k[4]))
    # Ignore last in-progress candle if volume is very low (incomplete)
    # Simplified: use all candles
    return price, closes


def tick():
    """Run one tick: fetch data, process candle, return results."""
    data = get_feed_data()
    if data is None:
        return {"error": "Binance feed unavailable"}
    price, closes = data
    last = closes[-1]
    result = state.process_candle(last)
    result["price"] = price
    result["closes"] = closes
    return result


HTML_BODY = """\
    Price: {price}
    SMA5: {sma5}
    SMA20: {sma20}
    Cash: ${cash}
    BTC: {btc}
    Equity: ${equity}
    Signal: {signal}
    Trades:
    {trades_html}
"""

HTML_PAGE = """\
"""


class PaperHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass

    def _send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, body_text):
        html = HTML_PAGE.format(content=body_text)
        encoded = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok"})
        elif self.path == "/api/tick":
            result = tick()
            if "error" in result:
                self._send_json(result, code=502)
            else:
                self._send_json(result)
        elif self.path == "/":
            result = tick()
            if "error" in result:
                body = HTML_BODY.format(price="N/A", sma5="N/A", sma20="N/A",
                                         cash="N/A", btc="N/A", equity="N/A",
                                         signal="FEED ERROR", trades_html="")
                self._send_html(body)
            else:
                trades_html = ""
                for t in state.trades:
                    trades_html += (
                        f"{t['side']} {t['qty']} @ ${t['price']} "
                        f"({t['time']})")
                body = HTML_BODY.format(
                    price=result.get("price", "N/A"),
                    sma5=result.get("sma5") or "N/A",
                    sma20=result.get("sma20") or "N/A",
                    cash=result.get("cash", "N/A"),
                    btc=result.get("btc", "N/A"),
                    equity=result.get("equity", "N/A"),
                    signal=result.get("signal", "-"),
                    trades_html=trades_html)
                self._send_html(body)
        else:
            self.send_response(404)
            self.end_headers()


server = http.server.ThreadingHTTPServer(
    ("0.0.0.0", PORT), PaperHandler)
print(f"Paper server on port {PORT}")
server.serve_forever()
