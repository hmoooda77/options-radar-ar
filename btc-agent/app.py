"""Bitcoin paper trading agent with analysis engine. Pure Python, no external frameworks."""

import http.server
import json
import os
import sys
import urllib.request
import threading
import base64
from pathlib import Path

PORT = int(os.environ.get("PORT", "10000"))

# Add parent directory to path so engine module is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import PaperTrader, analyze

_trader = PaperTrader(starting_cash=10.0, fee_rate=0.001)
_last_analysis = None


def fetch_json(url, timeout=8):
    """Fetch and parse JSON from a URL."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def get_tick_data():
    """Fetch current price and recent candles from Binance.

    Raises exceptions on any market-data failure.
    """
    price_data = fetch_json(
        "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    )
    price = float(price_data["price"])

    candles = fetch_json(
        "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=60"
    )

    # Parse klines: [open_time, open, high, low, close, volume, ...]
    parsed = []
    for c in candles:
        parsed.append((
            float(c[1]),   # open
            float(c[2]),   # high
            float(c[3]),   # low
            float(c[4]),   # close
            float(c[5]),   # volume
        ))

    return price, parsed


def run_tick():
    """Run a single analysis + paper-trading tick."""
    global _last_analysis
    try:
        price, candles = get_tick_data()
    except Exception as e:
        _last_analysis = {
            "error": "Market data unavailable",
            "detail": str(e),
            "mode": "PAPER ONLY",
        }
        return

    if len(candles) >= 50:
        analysis = analyze(candles)
        if analysis is not None:
            result = _trader.tick(candles)
            _last_analysis = result
            return

    # Fallback: return last known analysis or a minimal response
    if _last_analysis is None:
        _last_analysis = {"error": "Not enough candles", "mode": "PAPER ONLY"}


class Handler(http.server.BaseHTTPRequestHandler):
    """Simple HTTP handler for the paper-trading agent API."""

    def log_message(self, *args):
        pass  # Suppress default logging

    def send_json(self, code, obj):
        """Send a JSON response."""
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/health":
            return self.send_json(200, {"status": "ok", "mode": "paper"})

        if path == "/api/tick":
            try:
                run_tick()
                if _last_analysis is not None:
                    return self.send_json(200, _last_analysis)
                else:
                    return self.send_json(200, {"error": "No data yet", "mode": "PAPER ONLY"})
            except Exception as e:
                return self.send_json(502, {
                    "error": "Market data unavailable",
                    "detail": str(e),
                    "mode": "paper",
                })

        if path == "/":
            html = """\
    "html": True  # HTML content below
"""
            html_page = """\
"""
            return self.send_json(404, {"error": "Not found"})


def main():
    """Start the HTTP server."""
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Paper agent listening on port {PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
