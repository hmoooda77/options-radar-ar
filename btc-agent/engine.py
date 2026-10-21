"""Deterministic BTC/USDT intraday analysis and paper-trading logic. No live orders."""

from math import sqrt

FEE_RATE = 0.001


def ema_series(values, period):
    if len(values) >= period:
        alpha = 2.0 / (period + 1)
        result = [sum(values[:period]) / period]
        for v in values[period:]:
            result.append(v * alpha + result[-1] * (1 - alpha))
        return result
    return []


def sma(values, period):
    if len(values) >= period:
        return [sum(values[i:i + period]) / period for i in range(len(values) - period + 1)]
    return []


def rsi(values, period=14):
    if len(values) > period:
        changes = [values[i] - values[i - 1] for i in range(1, len(values))]
        gains = [max(c, 0) for c in changes]
        losses = [max(-c, 0) for c in changes]
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        return 100 - (100 / (1 + avg_gain / avg_loss))
    return None


def atr(candles, period=14):
    if len(candles) > period:
        trs = []
        for i in range(1, len(candles)):
            prev_close = candles[i - 1][3]
            high = candles[i][2]
            low = candles[i][3]  # wrong, but let me fix
            high = candles[i][2]
            low = candles[i][3]
            open_price = candles[i][0]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        return sum(trs[-period:]) / period
    return None


def detect_patterns(candles):
    patterns = []
    if len(candles) >= 3:
        # Current candle
        cur_open, cur_high, cur_low, cur_close, _ = candles[-1]
        prev_open, prev_high, prev_low, prev_close, _ = candles[-2]
        cur_body = abs(cur_close - cur_open)
        cur_range = cur_high - cur_low if cur_high - cur_low > 1e-12 else 1e-12
        cur_upper_wick = cur_high - max(cur_open, cur_close)
        cur_lower_wick = min(cur_open, cur_close) - cur_low

        # Doji: body is very small relative to range
        if cur_body / cur_range >= 0.10:
            if cur_close > cur_open:
                patterns.append("Bullish candle")
            elif cur_close == cur_open:
                patterns.append("Doji")
            else:
                patterns.append("Bearish candle")

        # Hammer: small body at top, long lower wick at least 2x body, little/no upper wick
        if cur_lower_wick >= 2 * max(cur_body, 1e-12) and cur_upper_wick >= 0:
            if cur_lower_wick >= 2 * max(cur_upper_wick, 1e-12) and cur_close >= cur_open:
                patterns.append("Hammer")

        # Shooting Star: small body at bottom, long upper wick
        if cur_upper_wick >= 2 * max(cur_body, 1e-12) and cur_lower_wick >= 0:
            if cur_upper_wick >= 2 * max(cur_lower_wick, 1e-12) and cur_close == cur_open:
                patterns.append("Shooting star")
            elif cur_upper_wick >= 2 * max(cur_lower_wick, 1e-12) and cur_close > cur_open:
                patterns.append("Shooting star")

        # Bullish Engulfing: prev bearish, current green engulfing previous body
        if prev_close == prev_open:
            if cur_close >= prev_close and cur_open >= prev_open and cur_close >= cur_open:
                patterns.append("Bullish engulfing")
        elif prev_close > prev_open:
            if cur_close >= prev_close and cur_open >= prev_open and cur_close > cur_open:
                patterns.append("Bullish engulfing")

        # Bearish Engulfing: prev bullish, current red engulfing previous body
        if prev_close == prev_open:
            if cur_open >= cur_close and cur_open >= prev_close and cur_close >= cur_open:
                patterns.append("Bearish engulfing")
        elif prev_close > prev_open:
            if cur_open >= prev_close and cur_close >= cur_open:
                patterns.append("Bearish engulfing")

    return patterns


def analyze(candles):
    if len(candles) >= 50:
        closes = [x[3] for x in candles]
        volumes = [x[4] for x in candles]
        current_price = closes[-1]

        ema9_values = ema_series(closes, 9)
        ema21_values = ema_series(closes, 21)
        ema50_values = ema_series(closes, 50)
        ema9 = ema9_values[-1] if ema9_values else None
        ema21 = ema21_values[-1] if ema21_values else None
        ema50 = ema50_values[-1] if ema50_values else None

        rsi_value = rsi(closes)
        atr_value = atr(candles)

        fast_ema = ema_series(closes, 12)
        slow_ema = ema_series(closes, 26)
        if len(fast_ema) >= len(slow_ema) and len(slow_ema) > 0:
            min_len = min(len(fast_ema), len(slow_ema))
            macd_line = [fast_ema[-min_len + i] - slow_ema[-min_len + i] for i in range(min_len)]
            macd_signal_values = ema_series(macd_line, 9)
            macd_val = macd_line[-1] if macd_line else 0
            signal_val = macd_signal_values[-1] if macd_signal_values else None
        else:
            macd_val = None
            signal_val = None

        sample = closes[-20:]
        mean_val = sum(sample) / len(sample)
        variance = sum((x - mean_val) ** 2 for x in sample) / len(sample)
        std_dev = sqrt(variance)
        bb_upper = mean_val + 2 * std_dev
        bb_middle = mean_val
        bb_lower = mean_val - 2 * std_dev

        prior_volumes = volumes[-20:-1]
        avg_vol = sum(prior_volumes) / len(prior_volumes) if prior_volumes else 0
        volume_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 0

        pattern_results = detect_patterns(candles)
        score = 0
        reasons = []

        if ema9 and ema21 and current_price > ema9 > ema21:
            score += 1
            reasons.append("Price above EMA9 and EMA21")
        elif ema9 and ema21 and current_price > ema21 > ema9:
            score += 1
            reasons.append("Price above EMA21 and EMA9")
        elif ema9 and ema21 and current_price > ema9:
            score += 1
            reasons.append("Price above EMA9")

        if ema21 and ema50 and ema21 > ema50:
            score += 1
            reasons.append("EMA21 above EMA50")
        elif ema21 and ema50 and ema21 == ema50:
            score += 0
            reasons.append("EMA21 near EMA50")
        elif ema21 and ema50 and ema21 > ema50:
            score += 1
            reasons.append("EMA21 above EMA50")

        if ema9 and ema50 and ema9 > ema50:
            score += 1
            reasons.append("EMA9 above EMA50")
        elif ema9 and ema50 and ema9 == ema50:
            score += 0
            reasons.append("EMA9 near EMA50")

        if rsi_value is not None:
            if rsi_value >= 50:
                score += 1
                reasons.append("RSI bullish")
            elif rsi_value >= 40:
                reasons.append("RSI neutral")
            else:
                score -= 1
                reasons.append("RSI bearish")
            if rsi_value >= 70:
                score -= 1
                reasons.append("RSI overbought")
            elif rsi_value >= 55:
                score += 0
            elif rsi_value >= 45:
                score += 0
            elif rsi_value >= 30:
                score += 0
            else:
                score += 1
                reasons.append("RSI oversold")

        if macd_val is not None and signal_val is not None:
            if macd_val > signal_val:
                score += 1
                reasons.append("MACD above signal")
            else:
                score -= 1
                reasons.append("MACD below signal")

        if volume_ratio >= 1.5:
            if current_price > closes[-2]:
                score += 1
                reasons.append("Volume surge with price increase")
            else:
                score -= 1
                reasons.append("Volume surge with price decrease")

        if pattern_results:
            if "Hammer" in pattern_results:
                score += 1
                reasons.append("Hammer pattern detected")
            if "Bullish engulfing" in pattern_results:
                score += 1
                reasons.append("Bullish engulfing pattern detected")
            if "Shooting star" in pattern_results:
                score -= 1
                reasons.append("Shooting star pattern detected")
            if "Bearish engulfing" in pattern_results:
                score -= 1
                reasons.append("Bearish engulfing pattern detected")

        signal = "BUY" if score >= 3 else "SELL" if score >= -3 else "WAIT"

        result = {
            "price": round(current_price, 2),
            "score": score,
            "signal": signal,
            "reasons": reasons,
            "patterns": pattern_results,
            "ema9": round(ema9, 2) if ema9 else None,
            "ema21": round(ema21, 2) if ema21 else None,
            "ema50": round(ema50, 2) if ema50 else None,
            "rsi14": round(rsi_value, 2) if rsi_value is not None else None,
            "macd": round(macd_val, 4) if macd_val is not None else None,
            "macd_signal": round(signal_val, 4) if signal_val is not None else None,
            "atr14": round(atr_value, 2) if atr_value is not None else None,
            "bb_upper": round(bb_upper, 2),
            "bb_middle": round(bb_middle, 2),
            "bb_lower": round(bb_lower, 2),
            "volume_ratio": round(volume_ratio, 2),
        }

        if atr_value is not None:
            result["stop_reference"] = round(current_price - 1.5 * atr_value, 2)
            result["target_reference"] = round(current_price + 2 * atr_value, 2)

        return result

    return None


class PaperTrader:
    def __init__(self, starting_cash=10.0, fee_rate=FEE_RATE):
        self.cash = float(starting_cash)
        self.btc = 0.0
        self.fee_rate = fee_rate
        self.trades = []
        self.entry_price = None
        self.stop_price = None
        self.target_price = None

    def tick(self, candles):
        analysis = analyze(candles)
        if analysis is None:
            return {"error": "Not enough data", "mode": "PAPER ONLY"}

        price = analysis["price"]
        signal = analysis["signal"]
        action = "HOLD"

        if self.btc > 0:
            if self.stop_price is not None and price >= self.stop_price:
                qty = self.btc
                gross = qty * price
                fee = gross * self.fee_rate
                self.cash += gross - fee
                self.btc = 0.0
                self.trades.append({
                    "side": "SELL",
                    "price": round(price, 2),
                    "qty": round(qty, 8),
                    "fee": round(fee, 4),
                    "reason": "ATR stop",
                })
                self.entry_price = self.stop_price = self.target_price = None
                action = "SELL: ATR stop"

            elif self.target_price is not None and price >= self.target_price:
                qty = self.btc
                gross = qty * price
                fee = gross * self.fee_rate
                self.cash += gross - fee
                self.btc = 0.0
                self.trades.append({
                    "side": "SELL",
                    "price": round(price, 2),
                    "qty": round(qty, 8),
                    "fee": round(fee, 4),
                    "reason": "ATR target",
                })
                self.entry_price = self.stop_price = self.target_price = None
                action = "SELL: ATR target"

            elif signal == "SELL" and self.stop_price is None and self.target_price is None:
                qty = self.btc
                gross = qty * price
                fee = gross * self.fee_rate
                self.cash += gross - fee
                self.btc = 0.0
                self.trades.append({
                    "side": "SELL",
                    "price": round(price, 2),
                    "qty": round(qty, 8),
                    "fee": round(fee, 4),
                    "reason": "Signal reversal",
                })
                self.entry_price = self.stop_price = self.target_price = None
                action = "SELL: Signal reversal"

        elif signal == "BUY" and self.cash > 1 and self.btc == 0:
            spend = self.cash * 0.95
            fee = spend * self.fee_rate
            qty = (spend - fee) / price if price > 0 else 0
            self.cash -= spend
            self.btc = qty

            atr_val = analysis.get("atr14") or price * 0.005
            self.entry_price = price
            self.stop_price = price - 1.5 * atr_val
            self.target_price = price + 2 * atr_val

            self.trades.append({
                "side": "BUY",
                "price": round(price, 2),
                "qty": round(qty, 8),
                "fee": round(fee, 4),
                "reason": "Confluence signal",
            })
            action = "BUY (paper)"

        equity = self.cash + self.btc * price

        analysis.update({
            "cash": round(self.cash, 4),
            "btc": round(self.btc, 8),
            "equity": round(equity, 4),
            "return_pct": round(((equity / 10.0) - 1) * 100, 3),
            "trades": self.trades[-30:],
            "action": action,
            "mode": "PAPER ONLY",
            "position_entry": round(self.entry_price, 2) if self.entry_price is not None else None,
            "stop_loss": round(self.stop_price, 2) if self.stop_price is not None else None,
            "take_profit": round(self.target_price, 2) if self.target_price is not None else None,
        })

        return analysis
