# Byblos AI Suite

A production-oriented starter containing:

- `android-app/`: Android 6+ (API 23) Jetpack Compose application.
- `backend/`: Node.js backend that keeps `OPENAI_API_KEY` off the device and streams Responses API output with SSE.

## Security boundary

The Android application never contains the OpenAI API key. The key exists only in the backend environment. `BACKEND_API_TOKEN` is included only as an optional private-testing gate; it is extractable from an APK and is not a substitute for real user authentication.

Before a public release, replace the private-testing token with a real identity system such as Firebase Authentication, Auth0, an OIDC provider, or your company identity platform. Validate tokens on the backend and add Play Integrity as an abuse signal.

## Run locally

### 1. Backend

```bash
cd backend
cp .env.example .env
# Put your OpenAI key and an API model available to your project in .env.
npm install
npm test
npm start
```

The server listens on `http://localhost:3000` by default.

### 2. Android

Open `android-app/` in Android Studio. The debug build uses:

- Backend URL: `http://10.0.2.2:3000/`
- Token: empty by default

For a physical device, replace the debug URL in `app/build.gradle.kts` with your computer's LAN address or use an HTTPS development tunnel.

For a private test token, add this to `~/.gradle/gradle.properties` or the project's untracked `local.properties` integration:

```properties
BACKEND_API_TOKEN=replace-with-the-same-value-as-backend
```

Do not commit secrets.

## Release configuration

Build with:

```bash
cd android-app
./gradlew clean testDebugUnitTest connectedDebugAndroidTest
./gradlew bundleRelease \
  -PBACKEND_BASE_URL=https://api.your-domain.example/ \
  -PBACKEND_API_TOKEN=
```

For a public application, leave `BACKEND_API_TOKEN` empty and implement real user authentication before release.

## Included safeguards

- OpenAI key is server-side only.
- HTTPS-only release network policy.
- Request body limits, input validation, rate limiting, security headers, and an optional API token gate.
- Streaming responses over Server-Sent Events.
- Room persistence and a real v1-to-v2 migration test.
- ViewModel state management with `StateFlow`.
- R8 and resource shrinking in release builds.
- Unit, UI, migration, and backend endpoint tests.

## Still required before Google Play production

- Real authentication and per-user quotas.
- Privacy policy, terms, Data Safety declaration, deletion workflow, and consent language.
- Production domain, TLS, logging/monitoring, backups, and budget alerts.
- Play App Signing, upload key, store listing assets, internal/closed testing, and staged rollout.
- Device matrix testing on API 23 through API 37 and rooted/non-rooted risk testing when the app handles sensitive company data.
