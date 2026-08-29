---
name: interface-design
description: Design, implement, refactor, and holistically review distinctive production interfaces across UI polish, typography, color systems, accessibility, responsive layout, interaction states, motion, design-system architecture, data-dense dashboards, localization/RTL, and visual hierarchy. Use for web/app frontend creation or redesign, React/Next.js/HTML/CSS/Tailwind component work, admin and operational portals, Byblos business applications, accessibility/responsive audits, visual QA, design-system decisions, or requests such as "make this UI better", "make it premium", "review the whole interface", "redesign this page", or "fix the layout/accessibility/colors/typography".
---

# Byblos Interface Design

Treat interface quality as one system. Resolve the task mode, inspect the existing design context, define a deliberate direction when creation is in scope, route work to the owning references, implement in the project's idiom, and verify what users will actually experience.

## 1. Resolve the Task Mode

| Mode | Use when | Default behavior |
| --- | --- | --- |
| **Create** | New page, component, prototype, app, or design system | Establish a new visual language |
| **Redesign** | Existing interface should materially change its visual language | Replace weak/generic design decisions deliberately |
| **Refine** | Specific area should improve while the current system remains | Preserve project conventions and make scoped fixes |
| **Review** | User asks for audit, critique, QA, or findings | Remain read-only unless implementation is explicitly requested |

When several modes apply, choose the narrowest mode. Treat "make it completely different" as **Redesign**, not Refine.

## 2. Recon Before Design or Judgment

For an existing project, identify before editing:
- framework/runtime, router, and rendering model
- styling system and component library
- design tokens, spacing scale, colors, radii, shadows, and icon family
- typography stack and loaded weights
- existing motion library and interaction language
- supported themes, locales/RTL, viewport expectations, and density modes
- preview, test, lint, typecheck, and build commands

Preserve these conventions in **Refine** and **Review** unless they are the confirmed root cause. Do not introduce a second styling system or component library to solve an isolated problem.

## 3. Define the Aesthetic Direction Before Code

For **Create** and **Redesign**, answer these three questions first:
1. What problem does the interface solve, and for whom?
2. What single tone defines it: brutally minimal, maximalist, retro-futuristic, editorial, brutalist, art deco, organic, luxury, or playful?
3. What is the one visual or interaction idea users should remember?

Commit to one direction. Do not hedge between several aesthetics.

**Byblos Aesthetic Defaults (Create/Redesign):**
- Dark backgrounds with high-contrast accent colors (deep navy, charcoal, or near-black)
- Bold typography with clear weight hierarchy (display: 700+, body: 400/500)
- Generous whitespace with intentional density where data demands it
- Subtle depth via shadows and borders, not flat or neumorphic
- RTL-ready layout (Arabic CRM context)
- Professional, security-sector authority — never playful or consumer-casual

## 4. Implementation Rules (Non-Negotiable)

1. Every interactive element has a visible focus state
2. Color contrast meets WCAG AA minimum (4.5:1 text, 3:1 UI components)
3. No layout shift on load or theme toggle
4. Forms have associated labels, not placeholder-only labeling
5. Motion respects `prefers-reduced-motion`
6. No hardcoded pixel font sizes — use relative units (rem/em)
7. RTL flip via `dir="rtl"` and logical CSS properties, not mirrored CSS
8. Empty states, loading states, and error states are designed, not left blank
9. Touch targets ≥ 44px
10. No inline styles for theme values — use design tokens or CSS variables

## 5. Reference Map (Lazy Load)

Load only references relevant to the current task:

| Scope | Reference |
| --- | --- |
| Core workflow and task classification | `references/workflows.md` |
| Byblos brand aesthetic tokens | `references/byblos-aesthetic.md` |
| Accessibility audit and WCAG compliance | `references/accessibility.md` |
| Layout, grid, spacing, breakpoints | `references/layout.md` |
| Typography scale and font pairing | `references/typography.md` |
| Color systems and token design | `references/colors.md` |
| Motion, transitions, micro-interactions | `references/ui.md` |
| Design tokens, component architecture | `references/design-system.md` |
| Responsive, zoom, RTL, i18n | `references/responsive-i18n.md` |
| Tables, dashboards, data grids | `references/data-dense-ui.md` |
| Component implementation (React/HTML/CSS) | `references/frontend-implementation.md` |
| Rendered output visual QA | `references/visual-qa.md` |
| Labels, copy, microcopy, validation text | `references/interface-content.md` |
| Buttons, cards, forms, overlays | `references/component-patterns.md` |
| Byblos admin and service-business workflows | `references/business-apps.md` |
| Whole-screen or whole-flow audit | `references/interface-review.md` |
| Completion checklist before declaring done | `references/completion-criteria.md` |

## 6. Anti-Generic Design Gate

Before submitting any Create or Redesign output, verify:
- [ ] The design has a declared, committed aesthetic direction
- [ ] No Bootstrap/Material Design defaults left unstyled
- [ ] Typography uses intentional pairing — not system-ui with no hierarchy
- [ ] Colors are not the browser/framework default palette
- [ ] At least one memorable visual detail sets this design apart
- [ ] Spacing and density are deliberate, not default-margin inherited

If any item fails, revise before delivering.
