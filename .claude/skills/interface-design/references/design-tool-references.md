# Design Tool References

Curated tools for UI inspiration, component sourcing, and animation — used alongside the interface-design skill.

---

## 21st.dev — React Component Registry

Open-source community registry of copy-paste React UI components.

- **Format:** shadcn/ui registry format — install with `npx shadcn@latest add "https://21st.dev/r/<author>/<component>"`
- **Tech stack:** Tailwind CSS + Radix UI primitives
- **Model:** Browse free; 2 free copies/day; membership = unlimited + AI credits
- **Scale:** 1.4M+ developers, largest React component registry
- **Publishing:** Any author can publish; only needs `component.tsx` + `component.demo.tsx`
- **Use for:** Finding production-quality Tailwind/Radix components to drop into projects

```bash
# Install a component directly
npx shadcn@latest add "https://21st.dev/r/shadcn/accordion"
```

---

## refero.design/styles — UI Design Systems Library

Curated design research library extracted from real web products.

- **Library size:** 125,000+ real product screens, flows, and UI patterns
- **Styles layer:** Each style = a structured `DESIGN.md` file with tokens, typography, spacing, surfaces, component rules, imagery guidance, do/don't rules
- **Three research layers:**
  1. **Styles** — visual direction and design system tokens (refero.design/styles)
  2. **Screens** — concrete UI patterns and product decisions
  3. **Flows** — multi-step journey logic
- **MCP integration:** Refero MCP (launched October 2025) — connects to AI agents to provide design direction mid-task
- **Docs:** `doc.refero.design/mcp`
- **Use for:** Finding visual style direction before starting UI work; extracting design tokens from real products

---

## supahero.io — Hero Section Inspiration

Curated gallery of real website hero sections for landing page design.

- **Focus:** Website hero sections — layout, copy, CTAs, visual treatments
- **Model:** Proprietary, free to browse
- **Use for:** Landing page hero inspiration before writing/designing copy + layout

---

## motion.dev — Web Animation Library

Production-grade open-source animation library for React, JavaScript, and Vue.

- **License:** MIT
- **Version:** 13.5+ / 14.0+ (check changelog for exact features)
- **Core features:**
  - Hybrid JS + hardware-accelerated engine (the only dual library of its kind)
  - Independent transforms (x, y, rotate, scale without wrapper elements)
  - Scroll animation via ScrollTimeline (hardware-accelerated)
  - Layout animation with a single `layout` prop
  - Spring physics, gestures (hover, press, drag)
  - `AnimatePresence` for exit animations
  - Motion values + variants + stagger for complex sequences
- **Bundle size:** Core ~3.8 kb (Motion One variant); APIs described as 90% smaller than GSAP equivalents
- **Adoption:** Used by Framer and Figma; 460+ copy-paste examples in docs
- **Paid:** Motion+ adds AI kit, visual transition editor (IDE extension), premium components

```tsx
import { motion } from "motion/react"

<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0 }}
  transition={{ type: "spring", stiffness: 300 }}
>
  Hello
</motion.div>
```

---

## 60fps.design — Animation Inspiration Gallery

Curated gallery spotlighting smooth, buttery UI animations and transitions from real products.

- **Focus:** High-quality UI motion reference — scroll effects, page transitions, microinteractions
- **Model:** Free to browse
- **Use for:** Finding animation patterns from production apps to replicate in Motion/CSS

---

## Quick Routing Guide

| Need | Go to |
|---|---|
| Pre-built Tailwind React component | 21st.dev |
| Design system tokens from real product | refero.design/styles |
| Hero section layout inspiration | supahero.io |
| Add motion/animation to React/JS/Vue | motion.dev |
| Find animation pattern to replicate | 60fps.design |
