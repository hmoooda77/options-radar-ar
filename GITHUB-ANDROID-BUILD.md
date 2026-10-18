# GitHub Android APK build

1. Upload the contents of this project folder to the root of `hmoooda77/options-radar-ar` (replace the malformed flat files with this directory structure).
2. Commit the changes to the `main` branch.
3. In GitHub, open **Actions** and select **Build Android APK**. It starts automatically on pushes to `main`; it can also be started with **Run workflow**.
4. Wait for all steps to pass. Download `options-radar-ar-debug-apk` from the run's **Artifacts** section. The APK is not generated until that workflow finishes successfully.

The current API base URL is set in `public/runtime-config.js` to `https://options-radar-ar-fixed.onrender.com`. The Render service was created separately; test `https://options-radar-ar-fixed.onrender.com/api/health` before relying on live data. Yahoo Finance endpoints are unofficial and may be delayed or rate-limited. FINRA ATS summaries remain optional and require a separate token.
