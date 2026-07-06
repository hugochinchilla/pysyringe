# PySyringe Brand Kit

Brand identity for **PySyringe** (https://github.com/hugochinchilla/pysyringe).
Concept: *the API is the logo* — `Provide[pysyringe]`, set in JetBrains Mono.

## Assets (`kit/`)

| File | Size | Use |
|---|---|---|
| `banner.png` | 1200×300 | README banner (preferred: PNG renders identically everywhere) |
| `banner.svg` | 1200×300 | Vector banner; falls back to system monospace where webfonts are blocked (e.g. GitHub camo) |
| `og-image.png` | 1200×630 | Social preview / `<meta property="og:image">` |
| `logo-mark.svg` | 128×128 | App icon / favicon source (brackets + injection point); legible down to 16px |
| `wordmark-on-dark.svg` | 620×72 | Lockup for dark backgrounds |
| `wordmark-on-light.svg` | 620×72 | Lockup for light backgrounds (palette deepened one step for contrast) |

## Color

Dark (primary) context:
- `#0E1420` ink navy — background
- `#0A101C` well — code blocks, inset surfaces
- `#1C2A44` hairline borders · `#2A3A5C` hover borders
- `#5B8DEF` marker blue — `Provide`, links, accents
- `#FFD343` bracket yellow — the signal color (hover `#FFE175`)
- `#F3F5F9` primary text · `#8A97AC` secondary · `#5E6B80` tertiary
- `#3FB950` success green (sparingly)

Light context (wordmark-on-light): text `#12233F`, blue `#2D6FE0`, yellow `#D9A800`.

Usage: navy dominates; yellow is scarce — brackets, one CTA, eyebrows. Blue for anything interactive or "API".

## Type

- **JetBrains Mono** (400/500/700) — wordmark, code, labels, badges, annotations. Anything that could appear in an editor.
- **Space Grotesk** (400–700) — headings and prose. Anything that explains.
- Both on Google Fonts.

## Wordmark rules

- `Provide` blue · `[` `]` yellow · `pysyringe` near-white (dark) / ink (light)
- Always JetBrains Mono, never letter-spaced, never wrapped
- Favicon/avatar: use `logo-mark.svg`, not the wordmark
