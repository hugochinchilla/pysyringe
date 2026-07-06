# PySyringe — Brand & Web Design

Design system for **PySyringe** (https://github.com/hugochinchilla/pysyringe), an opinionated dependency-injection container for Python. Contains the brand identity assets and the design specs for the two web surfaces: the marketing/landing page and the documentation site.

## What's in here

```
design/
├── README.md            ← you are here (start here)
├── kit/                 ← brand assets + brand guidelines (kit/README.md)
├── landing/             ← landing page design spec
└── docs/                ← docs site design spec
```

Each subfolder has its own README with the full design spec. This file is the overview.

## The brand in one paragraph

Concept: **the API is the logo.** The wordmark is `Provide[pysyringe]` set in JetBrains Mono — `Provide` in marker blue, brackets in yellow, the name in near-white. Ink-navy backgrounds, one yellow signal color used sparingly (brackets, primary CTA, section eyebrows), blue for anything interactive or "API". JetBrains Mono for anything that could appear in an editor; Space Grotesk for anything that explains. Tagline: "Dependency injection that keeps your domain clean."

## Core tokens (dark, the primary context)

- `#0E1420` ink navy (background) · `#0A101C` well (code blocks, inset surfaces)
- `#1C2A44` hairline borders · `#2A3A5C` hover borders
- `#5B8DEF` marker blue · `#FFD343` bracket yellow (hover `#FFE175`) · `#3FB950` success green
- `#F3F5F9` primary text · `#8A97AC` secondary · `#5E6B80` tertiary · `#C9D4E3` code text

Light-theme equivalents and the full token table are in `docs/README.md`; brand usage rules in `kit/README.md`.

## 1. Brand kit (`kit/`)

| File | Size | Use |
|---|---|---|
| `banner.png` / `banner.svg` | 1200×300 | README banner (PNG preferred; the SVG falls back to system mono where webfonts are blocked) |
| `og-image.png` | 1200×630 | Social preview / `og:image` |
| `logo-mark.svg` | 128×128 | Favicon/app-icon source (navy tile, yellow brackets, blue injection point); legible to 16px |
| `wordmark-on-dark.svg` / `wordmark-on-light.svg` | 620×72 | Lockups |

`kit/README.md` has palette, type, wordmark rules, and repo application steps.

## 2. Landing page (`landing/`)

Single marketing page: sticky nav (logo, Docs/Features/PyPI links, GitHub button) → centered hero (`Provide[pysyringe]` wordmark at `clamp(40px,6vw,76px)`, tagline, badge row, copy-to-clipboard install chip + yellow "Read the docs" CTA) → two-column "THE IDEA" section with a code window (Django example) → six feature cards in an auto-fit grid on the darker well background (`[inject]`, `[Provide[T]]`, `[factory]`, `[override]`, `[contextvars]`, `[singleton]`) → footer. Dark only.

Interactions: install chip copies `pip install pysyringe` with a "copied!" flash; anchor links; hover color shifts (~150ms), no underlines anywhere. Full spec: `landing/README.md`.

## 3. Docs site (`docs/`)

The documentation pages. Three-column layout: sticky sidebar nav with `// GROUP` eyebrows · content column (max 760px) with breadcrumb, bordered h2 sections, always-dark syntax-highlighted code windows, `[!]` callouts, comparison card grids · sticky right "ON THIS PAGE" TOC.

Key features beyond layout:
- **Light + dark themes** — all colors flow through CSS custom properties on `body` / `body[data-theme="light"]`; toggle in header, persisted to localStorage. Code blocks intentionally stay dark in both themes.
- **Version selector** — header dropdown listing docs snapshots ("latest"/"viewing" tags); the URL is the source of truth for which version is shown.
- **Old-version banner** — sticky strip under the header on any non-latest snapshot: `[!] You are viewing the documentation for vX.Y.Z…` + "switch to {latest} →" chip. Not dismissible.

Full spec: `docs/README.md`.
