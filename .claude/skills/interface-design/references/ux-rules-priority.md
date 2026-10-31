# UX Rules Priority Table

10-category priority system for UI/UX quality control. Apply rules in priority order 1→10. Use as a pre-delivery checklist.

Source: ui-ux-pro-max skill (nextlevelbuilder, MIT)

## Priority Table

| Priority | Category | Impact | Key Checks (Must Have) | Anti-Patterns (Avoid) |
|---|---|---|---|---|
| 1 | **Accessibility** | CRITICAL | Contrast 4.5:1 minimum, Alt text on images, Full keyboard navigation, Aria-labels on interactive elements | Removing focus rings, Icon-only buttons without labels, Missing skip-links |
| 2 | **Touch & Interaction** | CRITICAL | Min tap target 44×44px, 8px+ spacing between targets, Loading state feedback, Touch response < 100ms | Hover-only interactions (no mobile equivalent), Instant state changes (0ms), No feedback on action |
| 3 | **Performance** | HIGH | WebP/AVIF images, Lazy load below fold, Reserve space to avoid CLS < 0.1, Code splitting | Layout thrashing, Cumulative Layout Shift, Render-blocking resources |
| 4 | **Style Selection** | HIGH | Match style to product type, Internal visual consistency, SVG icons (not emoji) | Mixing flat & skeuomorphic randomly, Emoji as UI icons, Style mismatch between pages |
| 5 | **Layout & Responsive** | HIGH | Mobile-first breakpoints, Viewport meta tag, No horizontal scroll, Max-width containers | Fixed px widths without max-width, Disabled user zoom, Missing viewport meta |
| 6 | **Typography & Color** | MEDIUM | Base body ≥ 16px, Line-height 1.5+, Semantic color tokens, Color contrast pass | Body text < 12px, Gray-on-gray text, Hardcoded hex colors in components |
| 7 | **Animation** | MEDIUM | Context-aware timing (50–300ms UI, 500–800ms narrative), Motion communicates meaning, Spatial continuity, `prefers-reduced-motion` respected | Same duration for every transition, Animating width/height (use transform/opacity), No reduced-motion support |
| 8 | **Forms & Feedback** | MEDIUM | Visible labels (not placeholder-only), Error message near the field, Helper text for complex inputs, Progressive disclosure | Placeholder as label, All errors shown only at top, Too many fields upfront |
| 9 | **Navigation** | HIGH | Predictable back behavior, Bottom nav ≤ 5 items, Deep linking works, Clear current location | Overloaded navigation (> 7 items), Broken back behavior, No breadcrumbs in deep hierarchies |
| 10 | **Charts & Data** | LOW | Legends, Tooltips, Accessible color coding (not color-alone) | Relying on color alone to convey data meaning, Missing axis labels |

## Design Dials (Apply During Design System Creation)

Three sliders that tune visual direction without changing content:

| Dial | Low (1–3) | Mid (4–7) | High (8–10) |
|---|---|---|---|
| **Variance** | Centered / minimal (biases toward minimalism) | Balanced / modern | Bold / asymmetric (biases toward brutalism, bento grids) |
| **Motion** | Subtle micro-interactions only | Standard scroll/stagger | Complex choreography (parallax, SplitText, Flip) |
| **Density** | Spacious (24–96px scale, marketing pages) | Standard (16–64px) | Dense (8–32px, dashboards, data tables) |

## Stack Detection (Before Styling)

Check these files to identify the project's framework before applying stack-specific guidance:

| File | Framework |
|---|---|
| `package.json` → react, next | React / Next.js |
| `package.json` → vue, nuxt | Vue / Nuxt |
| `package.json` → @angular | Angular |
| `package.json` → svelte | Svelte |
| `pubspec.yaml` | Flutter |
| `*.xcodeproj` or `Package.swift` | SwiftUI |
| `composer.json` | Laravel |
| `app.json` + `react-native` dep | React Native |

**Never assume a stack** — a wrong assumption silently misroutes every recommendation.

## Pre-Delivery Checklist

Run through these before marking any UI task complete:

- [ ] Contrast ratio passes for all text/background combinations
- [ ] All interactive elements are keyboard-reachable
- [ ] No icon-only buttons without aria-label
- [ ] Tap targets ≥ 44×44px on mobile
- [ ] No horizontal scroll at any breakpoint
- [ ] Images use WebP/AVIF with explicit width/height (no CLS)
- [ ] Loading and error states are handled
- [ ] `prefers-reduced-motion` respected for all animations
- [ ] Dark mode tested (if supported)
- [ ] RTL layout tested (for Byblos Arabic interface)
- [ ] Form errors appear near the relevant field, not only at the top
