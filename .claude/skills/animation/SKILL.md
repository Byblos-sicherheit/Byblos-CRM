---
name: animation
description: "Create, edit, or fix Lottie/Bodymovin JSON animations for the local Skia Skottie player — derived from text-to-lottie skill. Use for: logo animation, UI loaders/icons, typography reveals, lower thirds, data/stat animations, microinteractions, diagrams, product promos, camera/scene motion, visual effects, and SVG-to-Lottie conversion."
---

# Animation (Text-to-Lottie)

Authors production-ready Lottie JSON for the official local Skia Skottie player. The deliverable is a renderable scene, not isolated JSON.

## Operating Model

- Use the official Skottie player project for verification. Do not hand-roll a custom viewer.
- Prefer fewer questions and stronger defaults. Ask only when the decision materially changes the output (transparent vs. full-frame background, brand constraints, source assets).
- Prioritize clean, intentional, professional motion over merely satisfying the literal prompt.

## Reference Loading (load only what the task needs)

| User intent | References to read |
|---|---|
| Any new/edit/fix Lottie scene | `references/player-contract.md` — ALWAYS |
| JSON structure, keyframes, slots, shapes | `references/lottie-spec-map.md` |
| Logo animation | `references/recipe-logo.md`, `references/motion-taste.md`, `references/design-taste.md` |
| Typography, title, text reveal | `references/recipe-typography.md`, `references/design-taste.md` |
| Lower third, name tag, caption bar | `references/recipe-lower-thirds.md`, `references/design-taste.md` |
| Loader, icon, spinner, badge | `references/recipe-loaders-icons.md`, `references/motion-taste.md` |
| UI microinteraction | `references/recipe-ui-microinteractions.md`, `references/design-taste.md` |
| SVG-to-Lottie conversion | `references/recipe-svg-animation.md`, `references/svg-compatibility.md` |
| Camera, pan, zoom, parallax | `references/recipe-camera-scene-motion.md`, `references/design-taste.md` |
| Technical diagram, flow trace, callout | `references/recipe-diagram-technical.md` |
| Data, stats, KPIs, charts | `references/recipe-data-stats.md` |
| Product launch, social promo | `references/recipe-product-promo.md` |
| Glow, glass, metal, gradient effects | `references/recipe-visual-effects.md` |
| Multi-scene, chapters, transitions | `references/chapterization-transition-grammar.md` |

## Workflow

1. Read `references/player-contract.md` — confirms player setup and scene layout rules.
2. Route to relevant recipe reference(s) from the table above.
3. Draft the scene: layer structure → shape/text definitions → keyframes → timing.
4. Validate: check spec compliance, confirm player renders correctly.
5. Deliver the complete `.json` file.

## Player Setup (if missing)

```bash
npx degit diffusionstudio/lottie my-animation
cd my-animation && npm install && npm run dev
```

Vite prints the bound port on startup — use that port, never assume 3030.

## Design Defaults

- Clean, intentional motion — avoid busyness
- Default: looping, transparent background
- Easing: ease-out on entrances, ease-in on exits, spring for interactive feedback
- Duration: loaders 1.5-2.5s, reveals 0.6-1.2s, promos 3-8s
