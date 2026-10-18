import test from 'node:test';
import assert from 'node:assert/strict';
import { optionGreeks, summarizeChain, ema, rsi } from '../src/lib/options-analytics.js';

test('call and put delta are bounded and ordered', () => {
  const exp = Math.floor(Date.now()/1000) + 86400*30;
  const call = optionGreeks({spot:100,strike:100,iv:.3,expiry:exp,side:'CALL'});
  const put = optionGreeks({spot:100,strike:100,iv:.3,expiry:exp,side:'PUT'});
  assert.ok(call.delta > 0 && call.delta < 1);
  assert.ok(put.delta < 0 && put.delta > -1);
  assert.ok(call.gamma > 0 && put.gamma > 0);
});
test('chain summary computes an explicit heuristic and expected move', () => {
  const exp = Math.floor(Date.now()/1000) + 86400*7;
  const s = summarizeChain([{strike:100,side:'CALL',impliedVolatility:.3,openInterest:100,expiration:exp},{strike:100,side:'PUT',impliedVolatility:.3,openInterest:80,expiration:exp}],100,exp);
  assert.ok(s.expectedMove > 0);
  assert.equal(s.gammaWallStrike,100);
  assert.ok(Number.isFinite(s.netEstimatedGex));
});
test('EMA and RSI return usable values', () => {
  assert.equal(ema([1,2,3],2).length,3);
  assert.ok(rsi(Array.from({length:20},(_,i)=>i+1)) > 90);
});

import { theoreticalOptionPrice, deriveStockTargets, assessTradeEvidence } from '../src/lib/options-analytics.js';

test('target option pricing produces sensible call/put intrinsic bounds', () => {
  const expiry = Math.floor(Date.now()/1000) + 86400*30;
  const call = theoreticalOptionPrice({spot:110,strike:100,iv:0.3,expiry,side:'CALL'});
  const put = theoreticalOptionPrice({spot:90,strike:100,iv:0.3,expiry,side:'PUT'});
  assert.ok(call >= 10);
  assert.ok(put >= 10);
});

test('technical target levels derive from OHLC and ATR', () => {
  const candles = Array.from({length:20},(_,i)=>({time:`2026-09-${String(i+1).padStart(2,'0')}`,open:100+i,high:103+i,low:98+i,close:101+i,volume:1000}));
  const levels = deriveStockTargets(candles);
  assert.ok(levels.high20 > levels.close);
  assert.ok(levels.low20 < levels.close);
  assert.ok(levels.atr > 0);
});

test('trade evidence never asserts institutional identity', () => {
  const evidence = assessTradeEvidence({volume:10000,openInterest:1000,bid:1,ask:1.05,last:1.05,iv:.4});
  assert.match(evidence.classification,/غير محسوم/);
  assert.equal(evidence.volOi,10);
});
