# Open-source components and research sources

This project uses the following projects as dependencies or implementation references. No third-party repository is copied wholesale into this application; dependencies remain separately licensed.

- **TradingView Lightweight Charts** — https://github.com/tradingview/lightweight-charts — Apache-2.0. Used for the daily candlestick and volume chart. Retain required notices and attribution as required by its license.
- **technicalindicators** — https://github.com/anandanand84/technicalindicators — MIT. Added as an optional technical-indicator library dependency; the currently displayed EMA/RSI calculations are implemented locally in `src/lib/options-analytics.js`.
- **OptionsAnalytics** — https://github.com/oracl8/OptionsAnalytics — research reference for Black–Scholes, Greeks, implied volatility, volatility surfaces, and validation concepts. The application does not copy its source files.
- **OpenGreeks** — https://github.com/marketcalls/opengreeks — research reference for option pricing and higher-order Greeks. The application does not copy its source files.
- **awesome-options-analytics** — https://github.com/FlashAlpha-lab/awesome-options-analytics — discovery list for public options analytics tools and data providers.
- **Yahoo Finance public endpoints** — used as an unofficial free data source. Not an official stable API; rate limits, latency, and availability are not guaranteed. Check applicable terms before redistribution.

## Important analytics limitations

- Greeks and expected move are approximations calculated from available IV, spot, expiry, and a fixed illustrative risk-free rate.
- The GEX figure is a heuristic using call open interest as positive and put open interest as negative. Open interest alone does not identify dealer inventory or whether dealers are long/short gamma. Do not treat this as verified dealer positioning.
- Volume × last premium × contract multiplier is only an approximate notional turnover, not buyer-initiated options flow.
- The demo data is synthetic and must never be used as live market information.
- **options-flow-terminal** — https://github.com/ZayedBH/options-flow-terminal — مرجع معماري فقط؛ لم يتم نسخ الكود لأن حالة الترخيص غير واضحة، كما يوضح README أن Dark Pool placeholder يتطلب feed مدفوعًا.
- **options-flow-analytics** — https://github.com/igorfyago/options-flow-analytics — مرجع معماري فقط إلى حين التحقق من ملف LICENSE وتوافقه مع أي إعادة استخدام.
- **Options Strategy Backtesting** — https://github.com/OliverBarbeau/options-strategy-backtesting — مرجع لأساليب اختبار استراتيجيات الخيارات وحساب Greeks؛ لم يتم نسخ الكود.
- **FINRA OTC Transparency** — https://otctransparency.finra.org/otctransparency/ — مصدر رسمي عام لبيانات الشفافية خارج البورصة؛ لا يفترض التطبيق أنه feed لحظي للصفقات الفردية.
