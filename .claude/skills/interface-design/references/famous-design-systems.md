# Famous Design Systems (DESIGN.md Catalog)

100+ production design systems extracted from developer-focused websites, formatted as AI-readable DESIGN.md files. Use these to generate UI that matches a specific aesthetic or to study design patterns from world-class products.

Source: `voltagent/awesome-design-md` (MIT License)  
Base URL: `https://raw.githubusercontent.com/voltagent/awesome-design-md/main/design-md/`

## How to Use

Fetch any DESIGN.md and paste its contents into your prompt:

```
Read the Claude design system and generate a landing page that matches its aesthetic.
[paste DESIGN.md content]
```

Or reference specific token values from the design system to align your component.

## High-Priority for Byblos CRM

| Design System | Raw URL | Best for |
|---|---|---|
| **Claude** (Anthropic) | `design-md/claude/DESIGN.md` | Warm editorial, cream + coral, serif headlines |
| **Linear** | `design-md/linear.app/DESIGN.md` | Dark, minimal, sharp, developer tools |
| **Vercel** | `design-md/vercel/DESIGN.md` | Clean monochrome, extreme precision |
| **Stripe** | `design-md/stripe/DESIGN.md` | Financial trustworthiness, structured data |
| **Notion** | `design-md/notion/DESIGN.md` | Clean content-first, minimal chrome |
| **Figma** | `design-md/figma/DESIGN.md` | Tool UI, dense information, multi-panel |
| **Revolut** | `design-md/revolut/DESIGN.md` | Dark fintech, motion, premium feel |

## Full Catalog by Category

### AI & Developer Tools
- `design-md/claude/DESIGN.md` — Anthropic, warm cream + coral
- `design-md/cursor/DESIGN.md` — AI code editor
- `design-md/raycast/DESIGN.md` — macOS launcher, dark + vibrant
- `design-md/vercel/DESIGN.md` — Deployment platform
- `design-md/linear.app/DESIGN.md` — Project management
- `design-md/figma/DESIGN.md` — Design tool
- `design-md/notion/DESIGN.md` — Workspace

### SaaS & Productivity
- `design-md/stripe/DESIGN.md` — Payments
- `design-md/hubspot/DESIGN.md` — CRM
- `design-md/airtable/DESIGN.md` — Database UI
- `design-md/intercom/DESIGN.md` — Customer messaging
- `design-md/loom/DESIGN.md` — Video messaging

### Fintech
- `design-md/revolut/DESIGN.md`
- `design-md/coinbase/DESIGN.md`
- `design-md/binance/DESIGN.md` — Crypto exchange
- `design-md/robinhood/DESIGN.md` — Trading

### E-Commerce
- `design-md/shopify/DESIGN.md`
- `design-md/nike/DESIGN.md` — Athletic, bold
- `design-md/airbnb/DESIGN.md` — Warm hospitality

### Automotive & Premium
- `design-md/tesla/DESIGN.md` — Minimal luxury
- `design-md/bmw/DESIGN.md` — German precision
- `design-md/ferrari/DESIGN.md` — Italian luxury

### Entertainment
- `design-md/spotify/DESIGN.md` — Dark, music, green
- `design-md/netflix/DESIGN.md` — Dark, cinematic, red
- `design-md/youtube/DESIGN.md` — Video platform

### Retro & Nostalgic
- `design-md/windows-95/DESIGN.md` — 90s UI
- `design-md/geocities/DESIGN.md` — Early web

## Claude Design System Highlights

Fetched from `design-md/claude/DESIGN.md`:

**Core Identity:**
- Tinted cream canvas: `#faf9f5`
- Warm coral accent: `#cc785c`
- Dark navy surfaces: `#181715`
- "Warmest, most editorial interface in the AI product category"

**Typography:**
- Display: Copernicus/Tiempos Headline, weight 400, negative letter-spacing
- Body: StyreneB/Inter, humanist sans-serif
- Feel: literary publication, not standard SaaS

**Visual Rhythm:**
- 96px section padding
- 32px card padding
- Alternating cream ↔ dark navy surfaces
- Border radius: 8px buttons → 12px cards → 16px hero

**Primary Buttons:**
- Coral (#cc785c) exclusively on light surfaces
- Never inverted on dark surfaces

## Design Token Extraction Workflow

1. Fetch the target DESIGN.md from GitHub
2. Extract color tokens, typography stack, spacing values
3. Map to Tailwind theme extensions or CSS variables
4. Apply to your component/page with the extracted tokens

```css
/* Example: Claude-inspired tokens */
:root {
  --canvas: #faf9f5;
  --accent: #cc785c;
  --surface-dark: #181715;
  --text-primary: #1a1816;
  --radius-button: 8px;
  --radius-card: 12px;
  --section-gap: 96px;
}
```
