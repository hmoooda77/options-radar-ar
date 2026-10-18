import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
const app=express(); app.use(cors()); app.use(express.json());
const PORT=process.env.PORT||8787;
const headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36'};
const safeTicker=s=>String(s||'SPY').toUpperCase().replace(/[^A-Z.\-]/g,'').slice(0,8)||'SPY';
app.get('/api/health',(_,res)=>res.json({ok:true,provider:'Yahoo Finance public endpoints',mode:'free-unofficial',note:'Data availability and delay are controlled by provider.'}));
app.get('/api/options/:ticker',async(req,res)=>{
 const ticker=safeTicker(req.params.ticker);
 try{
  const url=`https://query1.finance.yahoo.com/v7/finance/options/${encodeURIComponent(ticker)}`;
  const r=await fetch(url,{headers}); if(!r.ok) throw new Error(`Yahoo returned ${r.status}`);
  const j=await r.json(); const root=j?.optionChain?.result?.[0]; if(!root) throw new Error('No option-chain data for this ticker');
  const quote=root.quote||{}; const expirationDates=root.expirationDates||[];
  const requested=req.query.expiry?Number(req.query.expiry):null;
  let chosen=root.options?.[0];
  if(requested && expirationDates.includes(requested)){
   const rr=await fetch(`${url}?date=${requested}`,{headers}); if(rr.ok){const jj=await rr.json();chosen=jj?.optionChain?.result?.[0]?.options?.[0]||chosen;}
  }
  const clean=x=>(x||[]).map(o=>({contractSymbol:o.contractSymbol||'',strike:o.strike??null,side:o.contractSymbol?.includes('C')?'CALL':'PUT',lastPrice:o.lastPrice??null,bid:o.bid??null,ask:o.ask??null,change:o.change??null,percentChange:o.percentChange??null,volume:o.volume??0,openInterest:o.openInterest??0,impliedVolatility:o.impliedVolatility??null,inTheMoney:!!o.inTheMoney,expiration:o.expiration??null,contractSize:o.contractSize||'REGULAR',currency:o.currency||'USD'}));
  res.json({ticker,asOf:new Date().toISOString(),source:'Yahoo Finance public endpoint',disclaimer:'مصدر مجاني غير رسمي؛ قد تتأخر البيانات أو تتوقف، ولا يضمن تدفقًا لحظيًا أو بيانات صفقات مؤسساتية.',quote:{price:quote.regularMarketPrice??null,change:quote.regularMarketChange??null,changePercent:quote.regularMarketChangePercent??null,previousClose:quote.regularMarketPreviousClose??null,currency:quote.currency||'USD',marketState:quote.marketState||'UNKNOWN'},expirationDates,selectedExpiration:chosen?.expirationDate??expirationDates[0]??null,calls:clean(chosen?.calls),puts:clean(chosen?.puts)});
 }catch(e){res.status(502).json({error:'تعذر جلب سلسلة الخيارات من المصدر المجاني.',details:e.message,ticker,help:'جرّب رمزًا شائعًا مثل SPY أو QQQ أو NVDA أو MU، أو استخدم وضع العرض التجريبي.'});}
});
app.get('/api/history/:ticker',async(req,res)=>{
 const ticker=safeTicker(req.params.ticker);
 try{
  const r=await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?range=3mo&interval=1d`,{headers});
  if(!r.ok) throw new Error(`Yahoo returned ${r.status}`);
  const j=await r.json(); const q=j?.chart?.result?.[0]; if(!q) throw new Error('No historical candles');
  const ts=q.timestamp||[], k=q.indicators?.quote?.[0]||{};
  const candles=ts.map((t,i)=>({time:new Date(t*1000).toISOString().slice(0,10),open:k.open?.[i],high:k.high?.[i],low:k.low?.[i],close:k.close?.[i],volume:k.volume?.[i]})).filter(x=>[x.open,x.high,x.low,x.close].every(v=>Number.isFinite(v)));
  res.json({ticker,candles,source:'Yahoo Finance public endpoint',asOf:new Date().toISOString(),disclaimer:'بيانات تاريخية من مصدر عام غير رسمي؛ قد تتأخر أو تتوقف.'});
 }catch(e){res.status(502).json({error:'تعذر جلب الشموع التاريخية.',details:e.message,ticker});}
});
app.get('/api/darkpool/:ticker',async(req,res)=>{
 const ticker=safeTicker(req.params.ticker);
 const token=process.env.FINRA_API_TOKEN;
 if(!token) return res.status(503).json({available:false,ticker,source:'FINRA OTC Transparency API',message:'FINRA_API_TOKEN غير مضبوط. هذا المصدر يعطي ملخصات ATS أسبوعية مجمعة، وليس شريط صفقات لحظي أو هوية المشترين.'});
 try{
  const payload={
   limit:20,
   fields:['issueSymbolIdentifier','issueName','totalWeeklyShareQuantity','totalWeeklyTradeCount','lastUpdateDate','summaryStartDate','summaryTypeCode','marketParticipantName'],
   compareFilters:[
    {compareType:'equal',fieldName:'issueSymbolIdentifier',fieldValue:ticker},
    {compareType:'equal',fieldName:'summaryTypeCode',fieldValue:'ATS_W_SMBL'}
   ]
  };
  const r=await fetch('https://api.finra.org/data/group/otcMarket/name/weeklySummary',{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json',Accept:'application/json','Data-API-Version':'1'},body:JSON.stringify(payload)});
  const raw=await r.text();
  if(!r.ok) throw new Error(`FINRA returned ${r.status}: ${raw.slice(0,220)}`);
  let rows; try{rows=JSON.parse(raw)}catch{throw new Error('FINRA response was not JSON')}
  res.json({available:true,ticker,source:'FINRA OTC Transparency API',period:'weekly aggregate',asOf:new Date().toISOString(),rows:Array.isArray(rows)?rows:[],disclaimer:'بيانات ATS أسبوعية مجمعة؛ ليست تدفقًا لحظيًا ولا تحدد جهة الشراء أو البيع أو هوية المؤسسة.'});
 }catch(e){res.status(502).json({available:false,ticker,source:'FINRA OTC Transparency API',message:'تعذر استرجاع ملخص FINRA. تحقق من صلاحية الرمز/التوكن وحدود الخدمة.',details:e.message});}
});
app.get('/api/quote/:ticker',async(req,res)=>{
 const ticker=safeTicker(req.params.ticker);
 try{const r=await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?range=5d&interval=5m`,{headers});if(!r.ok)throw new Error(`Yahoo returned ${r.status}`);const j=await r.json();const q=j?.chart?.result?.[0];if(!q)throw new Error('No quote data');const meta=q.meta||{};res.json({ticker,price:meta.regularMarketPrice??null,previousClose:meta.chartPreviousClose??meta.previousClose??null,currency:meta.currency||'USD',exchange:meta.exchangeName||'',marketState:meta.marketState||'UNKNOWN',source:'Yahoo Finance public endpoint',asOf:new Date().toISOString()});}catch(e){res.status(502).json({error:'تعذر جلب السعر.',details:e.message});}
});
const __dirname=path.dirname(fileURLToPath(import.meta.url));
if(process.env.NODE_ENV==='production'){app.use(express.static(path.join(__dirname,'../dist')));app.get('*',(req,res)=>res.sendFile(path.join(__dirname,'../dist/index.html')));}
app.listen(PORT,()=>console.log(`Options Radar API listening on ${PORT}`));
