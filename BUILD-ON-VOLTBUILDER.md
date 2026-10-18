# Options Radar AR — VoltBuilder upload package

This ZIP is structured for a Capacitor cloud build on VoltBuilder (not GitHub Actions).

## Build
1. Open https://volt.build/upload/ and sign in/create an account.
2. Upload this ZIP and select Android.
3. The config requests an APK debug build (`voltbuilder.json`).
4. Wait for the build result; download the APK only if VoltBuilder reports success.

## Important: live market data
The APK wrapper and the live-data API are separate. The app reads the public API address from `public/runtime-config.js` (or, optionally, `VITE_API_BASE_URL`). The options-chain request, charts, and FINRA panel all use the same base address now. This ZIP does not contain a deployed public API URL. Deploy the Node server to a public HTTPS host, verify `/api/health`, then set `window.OPTIONS_RADAR_API_BASE_URL = 'https://YOUR-ACTUAL-SERVICE-DOMAIN';` in `public/runtime-config.js` before the APK build. If you leave it blank in a native APK, the app deliberately falls back to labelled synthetic demo data rather than pretending to show live market data. FINRA ATS summaries also require `FINRA_API_TOKEN` on the backend; they are weekly aggregate data, not live institutional order flow.

This is a build input ZIP, not an APK. No APK has been built or verified by this packaging step.
