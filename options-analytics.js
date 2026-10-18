// Quantitative formulas adapted from standard Black-Scholes-Merton methodology.
// No market-position assumptions can reveal dealer inventory from open interest alone.
const SQRT2PI = Math.sqrt(2 * Math.PI);
export function normalPdf(x) { return Math.exp(-0.5 * x * x) / SQRT2PI; }
export function normalCdf(x) {
  const a = Math.abs(x), t = 1 / (1 + 0.2316419 * a);
  const d = 0.3989422804014327 * Math.exp(-a * a / 2);
  let p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
  if (x > 0) p = 1 - p;
  return p;
}
export function optionGreeks({ spot, strike, iv, expiry, side, now = Date.now(), rate = 0.04 }) {
  if (!(spot > 0 && strike > 0 && iv > 0 && expiry)) return null;
  const T = Math.max((Number(expiry) * 1000 - now) / (365.25 * 86400000), 1 / (365.25 * 24));
  const sigma = Math.min(Math.max(iv, 0.001), 5), rootT = Math.sqrt(T);
  const d1 = (Math.log(spot / strike) + (rate + sigma * sigma / 2) * T) / (sigma * rootT);
  const d2 = d1 - sigma * rootT;
  const call = String(side).toUpperCase() === 'CALL';
  const delta = call ? normalCdf(d1) : normalCdf(d1) - 1;
  const gamma = normalPdf(d1) / (spot * sigma * rootT);
  const theta = (-(spot * normalPdf(d1) * sigma) / (2 * rootT) - rate * strike * Math.exp(-rate * T) * (call ? normalCdf(d2) : normalCdf(-d2))) / 365;
  const vega = spot * normalPdf(d1) * rootT / 100;
  return { delta, gamma, theta, vega, T };
}
export function summarizeChain(chain, spot, expiry) {
  if (!(spot > 0) || !expiry || !chain?.length) return null;
  const enriched = chain.map(c => {
    const g = optionGreeks({ spot, strike: Number(c.strike), iv: Number(c.impliedVolatility), expiry: c.expiration || expiry, side: c.side });
    const oi = Number(c.openInterest) || 0;
    // Common heuristic only: call OI positive, put OI negative. Actual dealer inventory is unknown.
    const gex = g ? g.gamma * oi * 100 * spot * spot * 0.01 * (c.side === 'CALL' ? 1 : -1) : null;
    return { ...c, greeks: g, estimatedGex: gex };
  });
  const valid = enriched.filter(x => x.estimatedGex != null);
  const net = valid.reduce((s, x) => s + x.estimatedGex, 0);
  const byStrike = new Map();
  for (const x of valid) byStrike.set(x.strike, (byStrike.get(x.strike) || 0) + x.estimatedGex);
  const gammaWall = [...byStrike.entries()].sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0] || null;
  const atm = [...enriched].filter(x => x.impliedVolatility > 0).sort((a, b) => Math.abs(a.strike - spot) - Math.abs(b.strike - spot))[0];
  const T = Math.max((Number(expiry) * 1000 - Date.now()) / (365.25 * 86400000), 0);
  const iv = atm?.impliedVolatility || null;
  return { enriched, netEstimatedGex: net, gammaWallStrike: gammaWall?.[0] ?? null, gammaWallValue: gammaWall?.[1] ?? null, atmIv: iv, expectedMove: iv ? spot * iv * Math.sqrt(T) : null, atmStrike: atm?.strike ?? null };
}
export function ema(values, period) {
  const a = 2 / (period + 1); let prev = null;
  return values.map(v => { prev = prev == null ? v : v * a + prev * (1 - a); return prev; });
}
export function rsi(values, period = 14) {
  if (values.length <= period) return null;
  let gain = 0, loss = 0;
  for (let i = 1; i <= period; i++) { const d = values[i] - values[i - 1]; gain += Math.max(d, 0); loss += Math.max(-d, 0); }
  let ag = gain / period, al = loss / period;
  for (let i = period + 1; i < values.length; i++) { const d = values[i] - values[i - 1]; ag = (ag * (period - 1) + Math.max(d, 0)) / period; al = (al * (period - 1) + Math.max(-d, 0)) / period; }
  return al === 0 ? 100 : 100 - 100 / (1 + ag / al);
}

// Black–Scholes option mark estimate at a hypothetical underlying price/IV.
// This is a scenario estimate, not a market quote or guaranteed target.
export function theoreticalOptionPrice({ spot, strike, iv, expiry, side, now = Date.now(), rate = 0.04 }) {
  if (!(spot > 0 && strike > 0 && iv > 0 && Number(expiry) > 0)) return null;
  const T = Math.max((Number(expiry) * 1000 - now) / (365.25 * 86400000), 1 / (365.25 * 24 * 60));
  const sigma = Math.min(Math.max(iv, 0.001), 5), rootT = Math.sqrt(T);
  const d1 = (Math.log(spot / strike) + (rate + sigma * sigma / 2) * T) / (sigma * rootT);
  const d2 = d1 - sigma * rootT;
  const call = String(side).toUpperCase() === 'CALL';
  return call
    ? spot * normalCdf(d1) - strike * Math.exp(-rate * T) * normalCdf(d2)
    : strike * Math.exp(-rate * T) * normalCdf(-d2) - spot * normalCdf(-d1);
}

// Technical levels from OHLC candles: 20-session range, classic pivots, and ATR(14).
export function deriveStockTargets(candles = []) {
  const valid = candles.filter(c => [c.high, c.low, c.close].every(v => Number.isFinite(Number(v))));
  if (valid.length < 5) return null;
  const recent = valid.slice(-20), last = valid.at(-1), prev = valid.slice(-15);
  const highs = recent.map(c => Number(c.high)), lows = recent.map(c => Number(c.low));
  const tr = prev.map((c, i) => {
    const priorClose = i ? Number(prev[i - 1].close) : Number(c.close);
    return Math.max(Number(c.high) - Number(c.low), Math.abs(Number(c.high) - priorClose), Math.abs(Number(c.low) - priorClose));
  });
  const atr = tr.reduce((a, b) => a + b, 0) / tr.length;
  const high = Math.max(...highs), low = Math.min(...lows), close = Number(last.close);
  const pivot = (Number(last.high) + Number(last.low) + close) / 3;
  return { close, high20: high, low20: low, pivot, r1: 2 * pivot - Number(last.low), s1: 2 * pivot - Number(last.high), r2: pivot + (Number(last.high) - Number(last.low)), s2: pivot - (Number(last.high) - Number(last.low)), atr, atrUp: close + atr, atrDown: close - atr, asOf: last.time };
}

// Heuristic confidence score is an evidence checklist, not a claim about participant identity.
export function assessTradeEvidence({ volume = 0, openInterest = 0, bid = null, ask = null, last = null, iv = null } = {}) {
  const volOi = openInterest > 0 ? volume / openInterest : null;
  const spreadPct = bid > 0 && ask >= bid ? (ask - bid) / ((ask + bid) / 2) * 100 : null;
  const nearAsk = bid > 0 && ask >= bid && last != null ? (last - bid) / (ask - bid || 1) : null;
  const flags = [];
  if (volOi != null && volOi >= 1) flags.push('حجم اليوم يساوي/يتجاوز OI');
  if (spreadPct != null && spreadPct <= 8) flags.push('فارق سعري ضيق نسبيًا');
  if (nearAsk != null && nearAsk >= 0.75) flags.push('آخر سعر قرب Ask (ليس إثبات شراء)');
  if (iv != null && iv >= 0.8) flags.push('تقلب ضمني مرتفع جدًا؛ انتبه لانكماش IV');
  return { volOi, spreadPct, nearAsk, flags, classification: 'غير محسوم — لا يمكن استنتاج هوية مؤسسية من بيانات العقد وحدها' };
}
