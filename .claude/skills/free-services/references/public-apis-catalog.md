# Public APIs Catalog

Curated list of 1,400+ free public APIs across 80+ categories. All entries are free (free tier or no auth required) and community-verified.

Source: `public-apis/public-apis` (MIT) · github.com/public-apis/public-apis

---

## How to Use in Free Services Skill

When a user asks "find a free API for X" or "is there a free API for Y":

1. Check this catalog first for known free options
2. Filter by: Auth type (no auth preferred → apiKey → OAuth), HTTPS=Yes, CORS=Yes for browser apps
3. Use the API format reference below to evaluate entries

### API Entry Format

```
| API Name (link) | Description | Auth | HTTPS | CORS |
```

- **Auth**: `No` = no auth needed · `apiKey` = register for key · `OAuth` = OAuth flow
- **HTTPS**: `Yes` = secure · `No` = avoid for production
- **CORS**: `Yes` = usable in browser · `No` = server-side only · `Unknown` = test first

---

## Top Categories for Byblos Projects

### Security & Identity
- HaveIBeenPwned — breach lookup by email (apiKey, HTTPS, No CORS)
- Shodan — internet device search (apiKey, HTTPS, No CORS)
- AbuseIPDB — IP abuse reports (apiKey, HTTPS, Yes CORS)
- VirusTotal — file/URL/IP scanning (apiKey, HTTPS, No CORS)

### Development & Tooling
- GitHub — repos, issues, PRs (OAuth, HTTPS, Yes CORS)
- GitLab — CI/CD, repos (OAuth, HTTPS, Unknown CORS)
- OpenAI / Groq / OpenRouter — LLM inference (apiKey — see `/free-services` → `free-llm-apis.md`)
- Postman Echo — API testing/echo (No, HTTPS, Yes CORS)

### Business & Finance
- Open Exchange Rates — currency rates (apiKey free tier, HTTPS, Yes CORS)
- REST Countries — country data (No, HTTPS, Yes CORS)
- Abstract API — email validation, phone, IP geolocation (apiKey free tier)

### Communication
- Twilio — SMS (apiKey, HTTPS; free trial credits)
- EmailJS — client-side email (apiKey, HTTPS, Yes CORS)
- Mailgun — transactional email (apiKey, HTTPS; 100 emails/day free)

### Maps & Location
- OpenStreetMap Nominatim — geocoding (No, HTTPS, Yes CORS) — GDPR-safe EU alternative to Google Maps
- ipapi.co — IP → location (No/apiKey, HTTPS, Yes CORS)
- What3words — 3-word address lookup (apiKey, HTTPS, Yes CORS)

### Data & AI
- Wikipedia — article content (No, HTTPS, Yes CORS)
- Hugging Face Inference — 100+ free ML models (No/apiKey, HTTPS, Yes CORS)
- NASA APIs — space imagery, asteroids, APOD (No/apiKey, HTTPS, Yes CORS)

---

## Evaluation Checklist (before recommending an API)

```
□ Auth: No or apiKey (OAuth adds friction for quick projects)
□ HTTPS: Yes (non-negotiable for production)
□ CORS: Yes (if used in browser/frontend; No is OK for backend)
□ Free tier: documented, no credit card required if possible
□ Rate limit: fits the expected workload
□ Data residency: EU-hosted or GDPR-compliant for DE clients
□ Uptime/SLA: check status page or uptime history
```

---

## Finding APIs Not in This List

If the catalog doesn't cover a specific need, search:
- **RapidAPI Hub** — rapidapi.com/hub (largest API marketplace, many free tiers)
- **Postman API Network** — postman.com/explore
- **APIs.guru** — apis.guru (OpenAPI specs for 2,400+ APIs)
- **ProgrammableWeb** — programmableweb.com (API directory, now archived but searchable)

---

## Fetching the Full Catalog

The full catalog README (1,400+ entries) lives at:
```
https://github.com/public-apis/public-apis/blob/master/README.md
```

It is structured as markdown tables grouped by category. For programmatic access, a JSON mirror is maintained at:
```
https://api.publicapis.org/entries  (unofficial, community-run)
```

Query example:
```bash
curl "https://api.publicapis.org/entries?category=Security&https=true&cors=yes"
```
