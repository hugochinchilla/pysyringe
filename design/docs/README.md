# PySyringe Docs Site — Design Spec

## Overview
Documentation pages for **PySyringe** (https://github.com/hugochinchilla/pysyringe) in the "Provide[pysyringe]" brand system, with **light and dark themes** and a **version selector** across the docs snapshots kept for previous releases. Layout, tokens, and components are high-fidelity; the content is the project's real documentation rendered in this system.

## Design Tokens (CSS custom properties — copy verbatim)

Dark theme (default, on `body`):
`--bg:#0E1420; --well:#0A101C; --line:#1C2A44; --line2:#2A3A5C; --text:#F3F5F9; --text2:#8A97AC; --text3:#5E6B80; --blue:#5B8DEF; --yellow:#FFD343; --yellow-ink:#FFD343; --green:#3FB950; --code-text:#C9D4E3; --nav-bg:rgba(14,20,32,0.92)`

Light theme (`body[data-theme="light"]`):
`--bg:#F6F7F9; --well:#FFFFFF; --line:#E0E4EA; --line2:#C6CEDA; --text:#12233F; --text2:#5E6B80; --text3:#8A97AC; --blue:#2D6FE0; --yellow:#D9A800; --yellow-ink:#B58900; --green:#1F8A3B; --nav-bg:rgba(246,247,249,0.92)`

**Code blocks are always dark** (`#0A101C` background, `#C9D4E3` text, `#1C2A44` borders) in BOTH themes — intentional brand decision.
Selection: `#FFD343` background, `#0E1420` text. `html { scroll-padding-top: 90px }` for anchor offset.

Type: JetBrains Mono (wordmark, code, labels, eyebrows, version chip) + Space Grotesk (headings, prose). Google Fonts, weights 400–700.

## Layout
Three-column: sticky left sidebar (240px) · main content (max 760px) · sticky right TOC (220px), centered in a 1400px container. Sticky header (z 10) at top; version banner (z 9) sticks directly below it at `top:65px`.

### Header
Logo mark (28px, `../kit/logo-mark.svg`) + "pysyringe" mono 16px bold + **version selector** + right links (Home, PyPI, GitHub ↗) + theme toggle button (mono, bordered, shows "☾ dark" / "☀ light").

### Version selector (key feature)
- Chip next to the logo: current version + ▾ caret, mono 11px, 1px `--line` border, radius 6px. Hover: border `--line2`.
- Click opens a dropdown: `--well` background, 1px `--line2` border, radius 8px, padding 6px, min-width 160px, shadow `0 8px 24px rgba(0,0,0,0.35)`, z 20.
- One row per version snapshot, mono 12px, padding 7px 10px, radius 6px, hover background `--bg`. Right-aligned tag mono 10px `--text3`: "latest" on the newest, "viewing" on the selected one. Selected row text is `--blue`, others `--text2`.
- Selecting a version navigates to that snapshot's URL, preserving the current page path when it exists in that snapshot. The URL is the source of truth for which version is shown.

### Old-version banner (key feature)
Shown only when the viewed snapshot is NOT the latest:
- Full-width strip under the header, sticky at `top:65px`, `--well` background, bottom border `--line`, padding 11px 32px, centered flex row, gap 14px.
- Contents: `[!]` glyph mono 12px in `--yellow-ink` · text 13.5px `--text2`: "You are viewing the documentation for **{version}**, which is not the latest release." (version in mono, `--text`) · action chip "switch to {latest} →" mono 12px `--blue`, 1px `--line2` border, radius 6px, padding 4px 10px, hover border `--blue`. Links to the same page in the latest snapshot.
- Not dismissible. Rendered on every page of a non-latest snapshot.

### Sidebar
Nav groups with mono 11px `// LABEL` eyebrows in `--yellow-ink` (`// START`, `// GUIDE`, `// ADVANCED`); items 14px `--text2`, padding 6px 10px, radius 7px, hover: text `--text` + background `--well`. The active page is marked with `--blue` text + a 2px left border in `--blue`.

### Main content patterns
- Breadcrumb: mono 12px `--text3` ("docs / getting started")
- h1 38px/700; h2 26px/700 with 1px `--line` top border + 18px padding-top; anchor ids on every h2
- Prose 15.5px `--text2` line-height 1.65; inline code mono 13.5px `--blue`
- Code windows: dark well, radius 12px, optional filename bar (mono 11px `--text3`, bottom border), pre 13px/1.7. Syntax colors: keywords `#5B8DEF`, strings/decorators/types `#FFD343`, comments `#5E6B80`, default `#C9D4E3`
- Callouts: bordered `--well` box, radius 10px, `[!]` glyph in `--yellow-ink`, body 14px `--text2`
- Two-up card grid for comparisons (singleton helpers): bordered cards radius 12px, mono `[tag]` title with yellow brackets + blue name
- Checklist rows: green ✓ mono glyph + 14.5px text
- Footer: top border, "pysyringe · MIT · Python ≥ 3.11" + "Edit on GitHub ↗"

### Right TOC
`// ON THIS PAGE` eyebrow + 13px `--text2` anchor links, hover `--blue`. The active section may be highlighted on scroll (optional).

## Interactions & Behavior
- **Theme toggle**: swaps `data-theme` on `<body>`; persists in `localStorage` key `pysyringe-docs-theme`; default dark. All colors flow through the CSS variables — no other JS needed.
- **Version dropdown**: toggles on chip click; closes on selection, outside click, or Escape.
- **Banner "switch to latest"**: navigates to the latest snapshot.
- Hovers are color/border shifts only, ~150ms; no underlines anywhere.
- Responsive: below ~1100px hide the right TOC; below ~900px collapse the sidebar behind a menu button; content gutter drops to 20–24px.

## Assets
From `../kit/` (see its README for brand rules): `logo-mark.svg` as the header mark and favicon source. Fonts from Google Fonts: JetBrains Mono, Space Grotesk.
