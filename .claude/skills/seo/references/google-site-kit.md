# Google Site Kit for WordPress SEO

Official Google plugin (v1.187.0+) that connects 9 Google services directly into the WordPress dashboard — no manual tag insertion or separate logins needed.

Source: `google/site-kit-wp` (Apache 2.0) · sitekit.withgoogle.com  
Requirements: WordPress ≥ 5.2, PHP ≥ 7.4

---

## Integrated Modules

| Module | What it provides for SEO |
|---|---|
| **Search Console** | Impressions, clicks, CTR, average position per query/page; index coverage; crawl issues |
| **Analytics 4 (GA4)** | Organic traffic breakdown, landing page performance, user behavior, conversion goals |
| **PageSpeed Insights** | Core Web Vitals (LCP / INP / CLS) per page, lab + field data, fix recommendations |
| **Tag Manager** | Deploy tracking tags and GTM containers without code; enables rich event tracking |
| **AdSense** | Revenue data per page, ad unit performance, auto-ad placement |
| **Ads** | Google Ads campaign performance; conversion tracking via site-wide tag |
| **Reader Revenue Manager** | Subscription and contribution widgets (Subscribe/Contribute with Google) |
| **Sign in with Google** | One-tap OAuth login block for WordPress pages |
| **Site Verification** | Proves ownership to Google Search Console without manual DNS/HTML changes |

---

## SEO Workflow Integration

### Initial Setup Order

1. Install plugin → Connect Google account (OAuth — no key needed)
2. Verify site ownership (automatic via Site Verification module)
3. Connect Search Console → grants impressions/ranking data inside WP
4. Connect Analytics 4 → grants traffic source breakdown
5. Connect PageSpeed Insights → grants CWV data per page
6. Optionally: connect Tag Manager, AdSense, Ads

### Core Web Vitals via Site Kit

PageSpeed Insights module shows CWV **per URL**, not just site-wide:
- LCP, INP (replaces FID), CLS with field data from Chrome UX Report (CrUX)
- Lab data from Lighthouse for pages not yet in CrUX
- Direct "Improve" links to actionable recommendations

Fix priority: address pages with most organic traffic first (cross-reference with Search Console data).

### Search Console + Analytics Combined View

Site Kit surfaces both in one dashboard widget:
- Clicks from Search Console + Sessions from GA4 → identify high-impression/low-click pages (CTR optimization opportunity)
- Bounce rate from GA4 alongside ranking data → identify pages where ranking does not convert

### Keyword Insights Workflow

1. Open Site Kit → Search Console tab
2. Filter by page → see which queries drive traffic to each page
3. Export to Looker Studio via GSC connector for deeper keyword clustering
4. Cross-reference with GA4 engagement metrics to identify high-intent queries

---

## WordPress-Specific SEO Settings (Complementary)

Site Kit does **not** manage on-page SEO (title tags, meta, schema). Pair with:

| Need | Plugin |
|---|---|
| Title/meta/schema | Yoast SEO or Rank Math |
| Sitemap | Yoast / Rank Math / XML Sitemap Generator |
| Image optimization | Smush, ShortPixel, or WebP Express |
| Caching (LCP/TTFB) | WP Super Cache, W3 Total Cache, or LiteSpeed Cache |
| CDN | Cloudflare (free tier) |

---

## Data Privacy / GDPR Notes

- Site Kit loads Google scripts (GA4, GTM, Ads) — requires cookie consent before firing
- Use Consent Mode v2 (via GTM or Consent Banner plugin) to stay GDPR-compliant in DE/EU
- Search Console and PageSpeed data: no personal data, no consent required
- Recommended consent plugins for DE: Borlabs Cookie, Complianz, or CookieYes

---

## Quick Reference: Site Kit Dashboard Sections

```
WordPress Admin → Site Kit
├── Dashboard       ← combined Search Console + Analytics overview
├── Search Console  ← queries, pages, CTR, impressions, positions
├── Analytics       ← traffic sources, pages, events, conversions
├── PageSpeed       ← CWV per URL (field + lab data)
├── AdSense         ← earnings per page
├── Ads             ← campaign performance
└── Settings        ← module connections, consent mode, data sharing
```

---

## Byblos Relevance

For Byblos CRM / WordPress-based client sites:
- **Local SEO**: Search Console shows which local queries ("Sicherheitsdienst Frankfurt") bring traffic
- **CWV fix loop**: PageSpeed → fix → PageSpeed re-check (Site Kit shows live field data)
- **Reporting**: Site Kit dashboard screenshots serve as client-ready SEO reports without manual export
