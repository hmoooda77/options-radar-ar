"""Deterministic BTC/USDT intraday analysis and paper-trading logic. No live orders."""
from math import sqrt

FEE_RATE = 0.001

def ema_series(values, period):
    if len(values) &lt; period: return []
 k=2.0/(period+1); out=[sum(values[:period])/period]
    for v in values[period:]: out.append(v*k+out[-1]*(1-k))
    return out

def rsi(values, period=14):
    if len(values)&lt;=period: return None
 changes=[values[i]-values[i-1] for i in range(1,len(values))]
 gains=[max(x,0) for x in changes[-period:]]; losses=[max(-x,0) for x in changes[-period:]]
 ag,al=sum(gains)/period,sum(losses)/period
    if al==0: return 100.0 if ag&gt;0 else 50.0
    return 100-100/(1+ag/al)

def atr(candles, period=14):
    if len(candles)&lt;period+1: return None
 tr=[]
    for i in range(1,len(candles)):
 _,_,h,l,_=candles[i]; prev=candles[i-1][3]
 tr.append(max(h-l,abs(h-prev),abs(l-prev)))
    return sum(tr[-period:])/period

def detect_patterns(c):
    if len(c)&lt;3: return []
 o,h,l,cl,_=c[-1]; po,ph,pl,pc,_=c[-2]
 body=abs(cl-o); rng=max(h-l,1e-12); upper=h-max(o,cl); lower=min(o,cl)-l
 out=[]
    if body/rng&lt;=.10: out.append("Doji")
    if lower&gt;=2*max(body,1e-12) and upper&lt;=body*.8 and cl&gt;=o: out.append("Hammer")
    if upper&gt;=2*max(body,1e-12) and lower&lt;=body*.8 and cl&lt;=o: out.append("Shooting star")
    if pc&lt;po and cl&gt;o and o&lt;=pc and cl&gt;=po: out.append("Bullish engulfing")
    if pc&gt;po and cl&lt;o and o&gt;=pc and cl&lt;=po: out.append("Bearish engulfing")
 a,b=c[-3],c[-2]; ab=abs(a[3]-a[0]); bb=abs(b[3]-b[0])
    if a[3]&lt;a[0] and bb&lt;ab*.45 and cl&gt;o and cl&gt;=(a[0]+a[3])/2: out.append("Morning-star-like")
    if a[3]&gt;a[0] and bb&lt;ab*.45 and cl&lt;o and cl&lt;=(a[0]+a[3])/2: out.append("Evening-star-like")
    return out

def analyze(candles):
    if len(candles)&lt;50: raise ValueError("Need at least 50 candles")
 closes=[x[3] for x in candles]; vols=[x[4] for x in candles]; price=closes[-1]
 e9,e21,e50=ema_series(closes,9)[-1],ema_series(closes,21)[-1],ema_series(closes,50)[-1]
 r=rsi(closes); a=atr(candles)
 fast,slow=ema_series(closes,12),ema_series(closes,26)
 macdline=[fast[i+14]-slow[i] for i in range(len(slow))]
 sigs=ema_series(macdline,9); macd=macdline[-1]; ms=sigs[-1] if sigs else None
 sample=closes[-20:]; mean=sum(sample)/20; sd=sqrt(sum((x-mean)**2 for x in sample)/20)
 vavg=sum(vols[-20:-1])/19 if sum(vols[-20:-1]) else 0; vr=vols[-1]/vavg if vavg else 0
 patterns=detect_patterns(candles); score=0; reasons=[]
    if price&gt;e9&gt;e21: score+=1; reasons.append("Price above EMA9 and EMA21")
    elif price&lt;e9&lt;e21: score-=1; reasons.append("Price below EMA9 and EMA21")
    if e21&gt;e50: score+=1; reasons.append("EMA21 above EMA50")
    elif e21&lt;e50: score-=1; reasons.append("EMA21 below EMA50")
    if r is not None:
        if 52&lt;=r&lt;=68: score+=1; reasons.append("RSI bullish, not extreme")
        elif r&gt;=75: score-=1; reasons.append("RSI extended")
        elif 32&lt;=r&lt;=48: score-=1; reasons.append("RSI weak")
        elif r&lt;=25: score+=1; reasons.append("RSI oversold; bounce unconfirmed")
    if ms is not None:
        if macd&gt;ms: score+=1; reasons.append("MACD above signal")
        else: score-=1; reasons.append("MACD below signal")
    if vr&gt;=1.5:
 reasons.append("Volume surge versus prior 19 candles")
        if candles[-1][3]&gt;candles[-1][0]: score+=1
        elif candles[-1][3]&lt;candles[-1][0]: score-=1
    if any(x in patterns for x in ("Hammer","Bullish engulfing","Morning-star-like")): score+=1
    if any(x in patterns for x in ("Shooting star","Bearish engulfing","Evening-star-like")): score-=1
 signal="BUY" if score&gt;=3 else "SELL" if score&lt;=-3 else "WAIT"
    return {"price":round(price,2),"score":score,"signal":signal,"reasons":reasons,"patterns":patterns,
      "ema9":round(e9,2),"ema21":round(e21,2),"ema50":round(e50,2),
      "rsi14":round(r,2) if r is not None else None,"macd":round(macd,4),
      "macd_signal":round(ms,4) if ms is not None else None,"atr14":round(a,2) if a else None,
      "bb_upper":round(mean+2*sd,2),"bb_middle":round(mean,2),"bb_lower":round(mean-2*sd,2),
      "volume_ratio":round(vr,2),"stop_reference":round(price-1.5*a,2) if a else None,
      "target_reference":round(price+2*a,2) if a else None}

class PaperTrader:
    def __init__(self, starting_cash=10.0, fee_rate=FEE_RATE):
 self.cash=float(starting_cash); self.btc=0.; self.fee_rate=fee_rate
 self.trades=[]; self.entry_price=None; self.stop_price=None; self.target_price=None
    def tick(self,candles):
 a=analyze(candles); p=a["price"]; sig=a["signal"]; action="HOLD"
        if self.btc&gt;0:
 reason="ATR stop" if self.stop_price and p&lt;=self.stop_price else "ATR target" if self.target_price and p&gt;=self.target_price else "Signal reversal" if sig=="SELL" else None
            if reason:
 qty=self.btc; gross=qty*p; fee=gross*self.fee_rate; self.cash+=gross-fee; self.btc=0.
 self.trades.append({"side":"SELL","price":p,"qty":qty,"fee":fee,"reason":reason})
 self.entry_price=self.stop_price=self.target_price=None; action="SELL: "+reason
        elif sig=="BUY" and self.cash&gt;1:
 spend=self.cash*.95; fee=spend*self.fee_rate; qty=(spend-fee)/p; self.cash-=spend; self.btc=qty
 self.entry_price=p; av=a["atr14"] or p*.005; self.stop_price=p-1.5*av; self.target_price=p+2*av
 self.trades.append({"side":"BUY","price":p,"qty":qty,"fee":fee,"reason":"Confluence signal"}); action="BUY (paper)"
 equity=self.cash+self.btc*p
 a.update({"cash":round(self.cash,4),"btc":round(self.btc,8),"equity":round(equity,4),
          "return_pct":round((equity/10-1)*100,3),"trades":self.trades[-30:],"action":action,
          "mode":"PAPER ONLY","position_entry":self.entry_price,
          "stop_loss":round(self.stop_price,2) if self.stop_price else None,
          "take_profit":round(self.target_price,2) if self.target_price else None})
        return a
