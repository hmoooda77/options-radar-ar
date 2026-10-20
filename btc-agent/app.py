#!/usr/bin/env python3
"""Bitcoin Paper-Trading Dashboard HTTP Server.
STANDARD LIBRARY ONLY - No external dependencies.
PAPER MODE ONLY - Does NOT place real orders.
"""
import http.server, json, time, threading, urllib.request, urllib.error, urllib.parse
import html, traceback, os
from collections import deque
from datetime import datetime, timezone

# ---- Configuration ----
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8080))
BINANCE_TICK = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
BINANCE_KLINE = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=25"
TIMEOUT = 10
INIT_CASH = 10.0
MAX_CASH_PCT = 0.90
FEE_PCT = 0.001

# ---- Simulated Trading State ----
class SimState:
    def __init__(self):
 self.lock = threading.Lock()
 self.cash = INIT_CASH
 self.position = 0.0
 self.history = []
 self.prev_sma5 = None
 self.prev_sma20 = None

    def _record(self, side, qty, price, pnl):
 eq = self.cash + self.position * price
 self.history.append({
            "side": side, "qty": round(qty, 8), "price": round(price, 2),
            "fee": round(abs(pnl), 6), "cash": round(self.cash, 4),
            "equity": round(eq, 4),
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        })

    def evaluate(self, price, sma5, sma20):
        with self.lock:
            fee = FEE_PCT
 mx = self.cash * MAX_CASH_PCT
 order = {"action": "HOLD", "price": round(price, 2)}
            if sma5 and sma20 and self.prev_sma5 and self.prev_sma20:
 crossed_up = self.prev_sma5 - self.prev_sma20
                curr_cross = sma5 - sma20
                if self.position == 0 and crossed_up - fee * mx * 0.01 > 0 and curr_cross + fee * mx * 0.01 > 0:
 spend = min(mx, self.cash)
                    if spend > 0:
                        qty = spend / price
                        cost = qty * price
 total = cost * (1 + fee)
                        if total > self.cash:
 qty = (self.cash * 0.95) / (price * (1 + fee))
                            cost = qty * price
 total = cost * (1 + fee)
 self.cash -= total
 self.position = qty
 self._record("BUY", qty, price, -total)
 order = {"action": "BUY", "qty": round(qty, 8), "price": round(price, 2)}
                elif self.position > 0 and crossed_up > 0 and curr_cross - fee * self.position * price * 0.02 - self.position * price * 0.01 > 0:
 rev = self.position * price
                    fa = rev * fee
 self.cash += rev - fa
 pnl = rev - fa - (self.position * self.position * price / max(self.position, 0.00000001)) if self.position > 0 else 0
 self._record("SELL", self.position, price, rev - fa)
 order = {"action": "SELL", "qty": round(self.position, 8), "price": round(price, 2)}
 eq = self.cash + self.position * price
 order.update({"equity": round(eq, 4), "cash": round(self.cash, 4),
                          "position": round(self.position, 8),
                          "sma5": round(sma5, 2), "sma20": round(sma20, 2)})
 self.prev_sma5, self.prev_sma20 = sma5, sma20
            return order

state = SimState()

# ---- Data ----
def _fetch(url):
 req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())

def get_price():
    return float(_fetch(BINANCE_TICK)["price"])

def get_closes():
    return [float(k[4]) for k in _fetch(BINANCE_KLINE)]

def ma(closes, p):
    return sum(closes[-p:]) / p if len(closes) >= p else None

# ---- HTTP Handler ----
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _j(self, code, obj):
 b = json.dumps(obj).encode()
 self.send_response(code); self.send_header("Content-Type","application/json")
 self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
 p = self.path.split("?")[0].rstrip("/") or "/"
        if p == "/health":
            return self._j(200, {"status":"ok","ts":datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
        if p == "/api/tick":
            try:
 pr = get_price(); cl = get_closes()
 s5 = ma(cl,5); s20 = ma(cl,20)
 od = state.evaluate(pr, s5, s20)
                return self._j(200, {"price":round(pr,2),"sma5":round(s5,2) if s5 else None,
                    "sma20":round(s20,2) if s20 else None,"order":od,
                    "history":state.history[-20:]})
            except Exception:
                return self._j(502, {"error":"Market data unavailable","detail":traceback.format_exc()[:200]})
 self._j(404, {"error":"Not found"})

# ---- Server ----
if __name__ == "__main__":
 srv = http.server.HTTPServer((HOST, PORT), H)
    print(f"Paper-trading dashboard on http://{HOST}:{PORT}")
    print("PAPER MODE ONLY - No real orders")
 srv.serve_forever()
