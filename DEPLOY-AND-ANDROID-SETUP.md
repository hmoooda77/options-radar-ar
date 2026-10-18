# Options Radar AR — backend and APK setup

## What was corrected
- The main options-chain request now uses the configured API base URL; previously it ignored `VITE_API_BASE_URL` while charts used it.
- Added `public/runtime-config.js` so the final public HTTPS backend address can be set before the APK build without rebuilding the source bundle by hand.
- Native Android builds without a backend URL explicitly use clearly labelled synthetic demo data rather than silently requesting `/api` from the local WebView origin.
- Chart/history and FINRA panels now report the missing API configuration instead of pretending that live data is available.
- Added a production Dockerfile, Render service blueprint, health endpoint usage, and relative manifest paths.

## Step 1 — deploy the backend
Deploy this project as a Node web service. The service runs `npm start` with `NODE_ENV=production`, builds `dist`, and serves both the web UI and `/api/*` routes from the same HTTPS origin. The health check is `/api/health`.

The included `render.yaml` is a deployment blueprint, but Render generally needs the source in a connected Git repository to deploy. The `Dockerfile` can be used by a container host that accepts a local/container build. No provider account or public service URL is embedded in this source package.

When deployment finishes, open `https://YOUR-ACTUAL-SERVICE-DOMAIN/api/health`. Continue only if it returns JSON containing `"ok":true`. Replace the example with the actual assigned domain; do not use localhost in a phone APK.

## Step 2 — configure the APK
Edit `public/runtime-config.js` and set the real HTTPS service URL:

```js
window.OPTIONS_RADAR_API_BASE_URL = 'https://YOUR-ACTUAL-SERVICE-DOMAIN';
```

Do not include `/api` at the end. Do not put the FINRA token here. Save, then rebuild the APK with the updated ZIP.

## Step 3 — validate
- Open `/api/health` on the deployed domain and verify `ok: true`.
- Check `/api/options/SPY` in a browser. A 502 can indicate Yahoo blocks/rate-limits the request; that is a data-provider issue, not an APK build issue.
- Build the APK with VoltBuilder and install it.
- In the installed app, test SPY and NVDA, then historical candles. Demo values must be labelled demo; do not trade on synthetic values.

## Data caveats
Yahoo Finance endpoints are unofficial and may throttle or stop responding. FINRA ATS output is weekly aggregate data and requires a backend-only token; it is not a real-time dark-pool tape and does not reveal buyer/seller identity. This project does not provide guaranteed real-time OPRA options data.

## Build locally (optional)
Node.js 20+ is recommended:

```bash
npm ci
npm test
npm run build
```

A successful web build does not itself prove an Android APK was generated. APK generation must be separately completed and verified by the Android build provider.
