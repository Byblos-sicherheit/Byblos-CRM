---
name: seo
description: Search engine optimization strategy, technical SEO, content SEO, local SEO, and SEO tooling. Covers keyword research, on-page optimization, technical audits, link building strategy, schema markup, Core Web Vitals, programmatic SEO, and local business SEO. Use for "SEO audit", "improve search ranking", "keyword research", "fix Core Web Vitals", "structured data", "local SEO", "backlink strategy", "meta tags", "sitemap", or any search optimization task. Optional MCP extensions available for Firecrawl, Ahrefs, DataForSEO, SE Ranking, and Unlighthouse integrations.
---

# SEO Skills

## Core SEO Workflow

1. **Audit first.** Identify existing issues before optimizing. Technical problems block all other SEO gains.
2. **Keyword strategy.** Map keywords to user intent (informational / navigational / commercial / transactional). One primary keyword per page; cluster related terms.
3. **On-page optimization.** Title tag, meta description, H1, URL structure, internal linking, image alt text.
4. **Technical SEO.** Crawlability, indexability, site speed, Core Web Vitals, structured data, sitemaps, robots.txt.
5. **Content SEO.** E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness), topical depth, content freshness.
6. **Link building.** Earn authoritative backlinks through content worth linking to. No spammy link schemes.
7. **Measure.** Track: organic traffic, rankings, CTR from Search Console, conversions from organic.

## Technical SEO Checklist

```
□ Robots.txt exists and is correct
□ XML sitemap submitted to Google Search Console
□ No duplicate content (canonical tags set)
□ HTTPS with valid certificate
□ Mobile-friendly (passes Google Mobile-Friendly Test)
□ Core Web Vitals: LCP < 2.5s, FID < 100ms, CLS < 0.1
□ Structured data (Schema.org) for primary content type
□ No broken links (4xx) in internal structure
□ No redirect chains (max 1 hop)
□ Hreflang set for multilingual content
□ Open Graph and Twitter Card meta tags set
□ Page title 50-60 chars; meta description 150-160 chars
□ Images have descriptive alt text; WebP format used
□ Lazy loading on below-fold images
```

## On-Page Optimization

**Title tag formula:** `[Primary Keyword] — [Brand Name]` or `[Action] [Primary Keyword] | [Brand]`

**Meta description:** Include primary keyword naturally; write a compelling reason to click (not just a keyword list). 150-160 characters.

**H1 rule:** One H1 per page; must contain primary keyword; should match or closely reflect title tag.

**URL structure:**
- Short and descriptive: `/services/security-consulting` not `/page?id=42`
- Lowercase, hyphens (not underscores), no stop words
- Depth: max 3 levels from root for important pages

**Internal linking:** Link to related pages with descriptive anchor text. Avoid "click here" or "read more" anchors.

## Schema.org Markup (Priority Types)

```json
// LocalBusiness (essential for Byblos)
{
  "@type": "LocalBusiness",
  "name": "Byblos Sicherheit & Facility Services",
  "address": { "@type": "PostalAddress", "addressCountry": "DE" },
  "telephone": "+49...",
  "openingHours": "Mo-Fr 08:00-18:00"
}

// Service
{
  "@type": "Service",
  "name": "Objektschutz",
  "provider": { "@type": "LocalBusiness", "name": "Byblos Sicherheit" }
}

// FAQPage — boosts SERP real estate
{
  "@type": "FAQPage",
  "mainEntity": [{ "@type": "Question", ... }]
}
```

## Local SEO (Byblos Priority)

1. **Google Business Profile**: complete all fields, add photos, post weekly updates, collect and respond to reviews
2. **NAP consistency**: Name, Address, Phone identical across all citations (website, GBP, directories, social)
3. **Local citations**: Gelbe Seiten, Das Örtliche, Yelp DE, Trustpilot DE, industry directories (BDSW, BDGW)
4. **Local landing pages**: one page per service area with localized content (not copy-paste)
5. **Reviews**: respond to every review within 48 hours; flag fake reviews via GBP reporting

## Keyword Research Process

1. Seed keywords from business services and customer language
2. Expand with: Google Suggest, People Also Ask, Search Console queries, competitor keywords
3. Classify by intent: informational (how to?) / commercial (best X?) / transactional (hire X / buy X)
4. Prioritize by: search volume × business relevance ÷ competition
5. Assign one primary keyword per page; group secondary/related keywords around it

## Core Web Vitals Fixes

| Metric | Target | Common Fixes |
|---|---|---|
| LCP (Largest Contentful Paint) | < 2.5s | Preload hero image, CDN, eliminate render-blocking CSS/JS |
| FID / INP (Interaction to Next Paint) | < 200ms | Break up long tasks, defer non-critical JS |
| CLS (Cumulative Layout Shift) | < 0.1 | Set explicit width/height on images and embeds, avoid dynamic content injection above fold |

## MCP Extensions (Optional — requires API keys)

These extensions unlock live data from external SEO tools. Each requires the corresponding MCP server configured with a valid API key:

| Extension | Capability | MCP Server |
|---|---|---|
| Firecrawl | Scrape competitor content, crawl site for SEO issues | `firecrawl` |
| Ahrefs | Keyword data, backlink analysis, rank tracking | `ahrefs` |
| DataForSEO | SERP data, keyword difficulty, local pack results | `dataforseo` |
| SE Ranking | Rank tracking, keyword research, competitor monitoring | `seranking` |
| Unlighthouse | Automated Core Web Vitals audits across the full site | `unlighthouse` |
| Bing Webmaster | Bing search performance and crawl data | `bing-webmaster` |

Without these MCP servers, provide strategy, checklists, and manually-implementable recommendations only.
