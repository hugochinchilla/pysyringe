# Handoff: PySyringe Docs Landing Page

## Overview
A single-page docs/marketing landing page for **PySyringe** (https://github.com/hugochinchilla/pysyringe), an opinionated dependency-injection container for Python. The page introduces the library with its new brand identity ("Provide[pysyringe]"), shows a code example, lists six features, and links to GitHub/PyPI. Goal: attract OSS contributors and look credible for production use.

## About the Design Files
The files in this bundle are **design references created in HTML** — prototypes showing intended look and behavior, not production code to ship. The task is to **recreate this design in the target codebase's environment** using its established patterns. If no environment exists yet, a static-site generator or plain HTML/CSS deployed to GitHub Pages (where the current docs live at hugochinchilla.net/pysyringe) is the most appropriate target — this page has almost no runtime logic.

`PySyringe Docs Landing.dc.html` is the reference design. It uses a proprietary component wrapper; read the markup inside `<x-dc>` for structure and the `class Component` script for data/behavior. All styles are inline on the elements — treat them as the spec.

## Fidelity
**High-fidelity.** Colors, typography, spacing, and copy are final. Recreate pixel-perfectly.

## Design Tokens

Colors:
- `#0E1420` ink navy — page background
- `#0A101C` well — code blocks, inset surfaces, badge/chip backgrounds
- `#1C2A44` hairline — borders, dividers
- `#2A3A5C` hairline-strong — hover borders
- `#5B8DEF` marker blue — `Provide`, links, code accents
- `#FFD343` bracket yellow — brackets, primary CTA background, section eyebrows (hover: `#FFE175`)
- `#F3F5F9` near-white — primary text
- `#8A97AC` slate — secondary text
- `#5E6B80` slate-dim — tertiary/labels
- `#C9D4E3` code default text
- `#3FB950` success green — checkmarks, "passing"
- Selection: background `#FFD343`, text `#0E1420`

Typography:
- **JetBrains Mono** (400/500/700) — wordmark, code, labels, nav GitHub button, badges, footer. Google Fonts.
- **Space Grotesk** (400–700) — headings and body prose. Google Fonts.
- Hero wordmark: JetBrains Mono, `clamp(40px, 6vw, 76px)`, line-height 1, nowrap
- Hero subtitle: 22px slate, max-width 640px
- Section headings: 34px, weight 700, letter-spacing -0.01em
- Section eyebrows: mono 13px, `#FFD343`, letter-spacing 0.06em, `// LABEL` style
- Body prose: 16px, line-height 1.6, slate
- Code: mono 13.5px, line-height 1.7
- Small labels/badges: mono 11–13px

Radii: 6px (badges), 8px (nav button), 10px (chips/CTAs/panels), 12px (feature cards), 14px (code window).
Spacing: page gutter 48px; section vertical padding 90–110px; content max-width 1120px; card padding 26px; grid gaps 20px.

## Screens / Views

One page, four regions top to bottom:

### 1. Nav (sticky)
- Full-width bar, padding 20px 48px, bottom border `#1C2A44`, background `rgba(14,20,32,0.92)` + `backdrop-filter: blur(8px)`, sticky top, z-index 10.
- Left: `kit/logo-mark.svg` at 32×32 + "pysyringe" mono 17px bold.
- Right (gap 28px): text links "Docs" (#docs anchor), "Features" (#features), "PyPI" (https://pypi.org/project/pysyringe/) — 14px slate, hover → near-white. Then "GitHub ↗" button: mono 13px, 8px 16px padding, 1px `#2A3A5C` border, radius 8px; hover: border+text `#5B8DEF`. Links to https://github.com/hugochinchilla/pysyringe.

### 2. Hero (centered column, padding 110px 48px 90px, gap 22px)
- Wordmark line: `Provide` in blue `#5B8DEF`, `[` `]` in yellow `#FFD343`, `pysyringe` in near-white.
- Subtitle (exact copy): "Dependency injection that keeps your domain clean. No decorators on your classes, no registration boilerplate — wiring happens at the call site."
- Badge row (toggleable): four chips, mono 11px, 1px `#1C2A44` border, radius 6px, padding 5px 12px: `tests passing` (green value), `coverage 100%` (green), `pypi v2.0.0` (blue), `license MIT` (slate). **Replace with real shields.io badges in production** (see repo README for URLs).
- CTA row (gap 14px):
  - Install chip: `$ pip install pysyringe` — mono 15px blue on `#0A101C`, 1px `#1C2A44` border, radius 10px, padding 14px 22px, `$` in slate-dim, trailing hint "click to copy" mono 11px slate-dim. Hover: border `#5B8DEF`. Click behavior below.
  - Primary CTA "Read the docs": 15px semibold, text `#0E1420` on `#FFD343`, radius 10px, padding 15px 24px; hover `#FFE175`. Anchors to #docs.

### 3. Code section (`id="docs"`, centered, bottom padding 100px)
Two columns (flex, gap 56px, max-width 1120px, wraps under ~800px):
- Left (min-width 320px): eyebrow `// THE IDEA`; heading "Your business logic should not know a container exists."; paragraph explaining `Provide[T]` markers (inline code words in mono blue); checklist row mono 13px slate-dim with green ✓: "typed", "framework-agnostic", "async-aware".
- Right (min-width 420px): code window — `#0A101C`, 1px `#1C2A44` border, radius 14px. Title bar: three 10px dots `#1C2A44`, filename mono 12px slate-dim, bottom border. Body: `<pre>` padding 22px 24px. The reference shows plain `#C9D4E3` text; **add Python syntax highlighting in production** using the token colors (keywords/decorators blue `#5B8DEF`, strings yellow `#FFD343`, comments `#5E6B80`).
- Three example snippets exist (see State Management): `views.py` (Django), `test_signup.py` (overrides), `factory.py`. Default: Django. Exact code is in the reference file's script block.

### 4. Features (`id="features"`, background `#0A101C`, top border `#1C2A44`, padding 90px 48px)
- Eyebrow `// FEATURES`, heading "Small API, sharp edges filed off."
- Grid: `repeat(auto-fit, minmax(320px, 1fr))`, gap 20px — 3×2 on desktop.
- Card: background `#0E1420`, 1px `#1C2A44` border (hover `#2A3A5C`), radius 12px, padding 26px, column gap 10px:
  - Tag: mono 14px — yellow `[` `]` around a blue keyword
  - Title 17px semibold, body 14px slate lh 1.6
- Six cards (tag / title / body):
  1. `[inject]` / Zero-decorator DI / "Your domain never imports the container. Injection happens only at call sites — HTTP handlers, CLI commands, consumers."
  2. `[Provide[T]]` / Explicit markers / "Only parameters annotated with Provide[T] are injected; the rest are left for the caller. Safe with any framework."
  3. `[factory]` / Factory-based wiring / "Resolve by return-type annotations on your factory, with recursive constructor inference for everything else."
  4. `[override]` / Test-friendly overrides / "Swap any dependency per test with a context manager. Cleanup is automatic, even when the test raises."
  5. `[contextvars]` / Thread & async safe / "Overrides are scoped to the current thread or asyncio task, so concurrent tests never leak state into each other."
  6. `[singleton]` / Singleton helpers / "singleton() shares thread-safe resources globally; thread_local_singleton() keeps unsafe ones per-thread."

### 5. Footer
Flex space-between, padding 28px 48px, top border `#1C2A44`. Left: logo mark 22px + "pysyringe · MIT · Python ≥ 3.10" mono 13px slate-dim. Right: "github.com/hugochinchilla/pysyringe" mono 13px slate, hover near-white, links to the repo.

## Interactions & Behavior
- Nav/text link hovers: color shift only, no underline anywhere.
- Install chip click: `navigator.clipboard.writeText('pip install pysyringe')`; hint text swaps to "copied!" for 1600ms, then back to "click to copy".
- Anchor links scroll to #docs / #features (smooth scrolling optional).
- Hero wordmark is `white-space: nowrap` and scales via clamp() — never let it wrap.
- Responsive: columns wrap via flex min-widths; feature grid collapses via auto-fit. At narrow widths reduce the 48px gutter to 20–24px and let the hero CTA row wrap.
- No entrance animations required; hover transitions ~150ms ease are fine.

## State Management
Minimal:
- `copied: boolean` — install-chip feedback, auto-resets after 1.6s.
- `codeExample: 'django' | 'tests' | 'factory'` — which snippet the code window shows (design-time toggle; production can hardcode Django or render tabs — ask the owner).
- `showBadges: boolean` — badge row visibility (production: show real badges).
No data fetching.

## Assets (in `kit/`)
All created in this project (no third-party imagery):
- `logo-mark.svg` — 128×128 navy tile, yellow brackets, blue dot; favicon source
- `wordmark-on-dark.svg` / `wordmark-on-light.svg`
- `banner.png` + `banner.svg` — 1200×300 README banner
- `og-image.png` — 1200×630 social preview (`<meta property="og:image">`)
Fonts from Google Fonts: JetBrains Mono, Space Grotesk.

## Files
- `PySyringe Docs Landing.dc.html` — the hi-fi reference (markup = layout spec, inline styles = style spec, script block = copy + code snippets + behavior)
- `kit/` — brand assets listed above
