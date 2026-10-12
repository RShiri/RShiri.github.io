---
name: Ram Shiri Portfolio
description: Graphite and hairlines, one signal accent, Geist; shipped sports-data work and playable charts carry the pitch.
colors:
  graphite-ground: "#0a0b0e"
  graphite-soft: "#111318"
  graphite-raise: "#161920"
  hairline: "#22262f"
  hairline-strong: "#323844"
  ink: "#f2f4f8"
  body: "#aeb4c0"
  muted: "#7f8796"
  signal: "#8ea6ff"
  signal-ink: "#0a0b0e"
  signal-soft: "rgba(142, 166, 255, .12)"
  status-ok: "#4ade80"
  pitch: "#0f1626"
  light-ground: "#fbfbfc"
  light-soft: "#f3f4f6"
  light-raise: "#ffffff"
  light-hairline: "#e3e5ea"
  light-hairline-strong: "#cfd3db"
  light-ink: "#0b0d12"
  light-body: "#3d4452"
  light-muted: "#626b7a"
  light-signal: "#2f55d4"
  light-signal-ink: "#ffffff"
  light-signal-soft: "rgba(47, 85, 212, .09)"
  light-status-ok: "#15803d"
typography:
  display:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(44px, 5.6vw, 78px)"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.04em"
    fontFeature: "\"ss01\", \"cv11\""
  headline:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(30px, 3.8vw, 44px)"
    fontWeight: 600
    lineHeight: 1.12
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.12
    letterSpacing: "-0.015em"
  lead:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(17px, 1.5vw, 18.5px)"
    fontWeight: 400
    lineHeight: 1.6
  body:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
    fontFeature: "\"ss01\", \"cv11\""
  label:
    fontFamily: "Geist, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "13.5px"
    fontWeight: 500
    lineHeight: 1.4
  data:
    fontFamily: "Geist Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "22px"
    fontWeight: 500
    lineHeight: 1
    fontFeature: "\"tnum\""
rounded:
  xs: "6px"
  sm: "8px"
  md: "10px"
  lg: "12px"
  card: "14px"
  portrait: "18px"
spacing:
  gutter: "24px"
  gutter-phone: "16px"
  card-gap: "16px"
  panel-inset: "22px"
  column-gap: "64px"
  section: "clamp(72px, 9vw, 120px)"
  container: "1160px"
components:
  button-solid:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.graphite-ground}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "0 18px"
    height: "42px"
  button-solid-hover:
    backgroundColor: "color-mix(in srgb, #f2f4f8 86%, #0a0b0e)"
  button-line:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 18px"
    height: "42px"
  button-small:
    rounded: "{rounded.sm}"
    padding: "0 13px"
    height: "34px"
  nav-link:
    textColor: "{colors.muted}"
    rounded: "{rounded.sm}"
    padding: "7px 11px"
  nav-link-hover:
    backgroundColor: "{colors.graphite-soft}"
    textColor: "{colors.ink}"
  stack-tag:
    textColor: "{colors.muted}"
    rounded: "{rounded.xs}"
    padding: "5px 7px"
  toggle-chip:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "7px 14px"
  toggle-chip-pressed:
    backgroundColor: "{colors.signal-soft}"
    textColor: "{colors.ink}"
  work-card:
    backgroundColor: "{colors.graphite-soft}"
    rounded: "{rounded.card}"
  viz-panel:
    backgroundColor: "{colors.graphite-ground}"
    rounded: "{rounded.card}"
  hero-card:
    backgroundColor: "{colors.graphite-soft}"
    rounded: "{rounded.portrait}"
    padding: "10px"
---

# Design System: Ram Shiri Portfolio

## Overview

**Creative North Star: "The Engineered Sheet"**

A precise, product-grade dark page in the Linear/Vercel tradition: near-black graphite ground, 1px hairlines that do all the structural work, Geist set tight and confident, and a single cool signal blue that appears only where something is live (links, focus, pressed state). The page is a standard professional portfolio in form; its distinction is finish, not novelty. Shipped work is framed like product shots inside a thin browser chrome, and the charts sit on their own dark pitch panels, which are data, not decoration.

Density is calm and generous at section level (sections breathe at 72 to 120px) and compact inside components (13 to 15px labels, 6 to 10px radii, 16px gaps). Motion is one load-in moment on the hero and small, functional state transitions everywhere else; nothing moves on scroll. Dark is the default; a light theme (`html[data-theme="light"]`) swaps every neutral and the signal for a paper-white counterpart while chart pitches stay dark.

The direction refuses glow, gradients used as brand fill, and emoji icons. Gradients appear only as tools: drawing the hairline grid behind the hero and masking it, and fading the edge of horizontally scrolling charts on phones.

**Key Characteristics:**
- Graphite ground in three tonal steps (ground, soft, raise) separated by 1px hairlines, not shadows.
- One signal accent for state and links only; primary buttons are ink-on-ground, not accent-filled.
- Geist for all text and display; Geist Mono with tabular figures for numerals and data readouts.
- Screenshots framed in a hairline browser chrome; charts on dark pitch panels in both themes.
- Dark default, full light theme, theme choice persisted under the shared `theme` key.

## Colors

A cool, near-monochrome graphite scale with one periwinkle signal; every hue beyond that lives inside the charts as data encoding.

### Primary
- **Signal Periwinkle** (`signal`, light theme `light-signal`): links, the focus ring, text selection, native `accent-color` (range slider), chip hover border, and the pressed state of chart tabs (border plus `signal-soft` tint). Never a fill for buttons or large surfaces.

### Neutral
- **Graphite Ground** (`graphite-ground` / `light-ground`): page background and chart panel background in dark mode.
- **Graphite Soft** (`graphite-soft` / `light-soft`): cards, the alternating analytics section band, hover fills on nav links and list rows.
- **Graphite Raise** (`graphite-raise` / `light-raise`): the screenshot stage inside work cards; chart panels in light mode.
- **Hairline** (`hairline` / `light-hairline`): every structural border, divider, list rule and the hero grid lines.
- **Hairline Strong** (`hairline-strong` / `light-hairline-strong`): hover border on cards and outline buttons, browser-chrome dots, scrollbar thumb.
- **Ink** (`ink` / `light-ink`): headings, emphasised values, and the solid button fill.
- **Body** (`body` / `light-body`): running text.
- **Muted** (`muted` / `light-muted`): secondary text, labels, captions, tags, legend text.

### Status
- **Live Green** (`status-ok` / `light-status-ok`): the availability dot only, with a 3px ring of itself at 22%.

### Data encoding (chart panels only)
- **Pitch** (`pitch`): the ground of every chart surface, identical in both themes so pale data lines stay legible.
- Chart inks are encoding, not brand: shots and goals #5b7cff / #2f6bff, on-target #e9f0fb, team home #74acdf, team away #2fbf71, won #34d399, failed / shot line #ff6b81, carry #ffd166, save #ffb020, xG readout #7cf3d0, F1 team colours from data. The chart tooltip is a fixed dark card (#0a0e18) in both themes.

### Named Rules
**The One Signal Rule.** The signal colour marks interactivity or state (link, focus, pressed, slider) and nothing else. A primary action is ink on ground.

**The Pitch Stays Dark Rule.** Chart surfaces use `pitch` and their own data palette in both themes; they are not re-themed with the UI neutrals.

## Typography

**Display Font:** Geist (with ui-sans-serif, system-ui)
**Body Font:** Geist
**Label/Mono Font:** Geist Mono (with ui-monospace, SFMono-Regular, Menlo)

**Character:** One engineered grotesk carries everything, tightened as it grows (letter-spacing from -0.015em at titles to -0.04em at display); the mono is reserved for numbers so data reads as instrument output. Stylistic sets `ss01` and `cv11` are on globally.

### Hierarchy
- **Display** (600, clamp(44px, 5.6vw, 78px), 1): the hero headline only; the contact closer uses the same voice at clamp(40px, 6vw, 72px).
- **Headline** (600, clamp(30px, 3.8vw, 44px), 1.12): section titles.
- **Title** (600, 17 to 24px, 1.12, -0.015em): card titles (17px), chart panel titles (18px), the featured work title (24px).
- **Lead** (400, clamp(17px, 1.5vw, 18.5px), 1.6): the hero introduction, max 60ch. Section subtitles are 17px in muted, max 62ch.
- **Body** (400, 16px, 1.65): running text; about copy at 17.5px / 1.7, max 62ch; card descriptions 14.5px.
- **Label** (500, 12 to 14.5px): nav links (14.5px), tags (12px), fact-sheet terms and chart captions (13.5px). Sentence case; no tracking-out, no uppercase.
- **Data** (Geist Mono 500, tabular figures): chart headline stats (22px), scores, positions, lap counters.

### Named Rules
**The Mono Means Measured Rule.** Geist Mono appears only on numerals and data readouts; prose, labels and headings stay in Geist.

**The Sentence Case Rule.** Labels and captions are sentence case at normal tracking; the build explicitly resets the legacy uppercase stat labels.

## Layout

A single centred container (1160px max, 24px gutters, 16px on phones). The hero is a two-column grid: copy in the flexible column, a 290px portrait card on the right, 64px apart and bottom-aligned, over a 64px hairline grid that fades out from the upper left. Sections stack with clamp(72px, 9vw, 120px) vertical padding; the analytics band alternates to `graphite-soft` with hairlines top and bottom. Section heads cap at 680px.

Selected work uses one full-width feature card (screenshot 1.45fr, text 1fr) followed by a two-column grid of peer cards with 16px gaps. **Open decision:** the four peer projects currently sit in an equal 2x2; the direction contract refuses equal-card grids and the user has not yet confirmed this arrangement, so neither the 2x2 nor an alternative is canonical.

Secondary builds are a hairline-ruled list (title, description, tags, arrow) rather than cards. About is a 1.25fr / 1fr split with 64px gap. Chart panels inset their content 22px.

Breakpoints: at 960px the hero, feature card and about collapse to one column and the portrait card becomes a horizontal 140px-image fact card; at 680px the grid goes single column, the nav becomes a dropdown sheet, contact buttons go full width, and wide charts render at a legible minimum width (920px F1, 720px win-prob) inside a horizontal scroller with a 48px faded edge.

## Elevation & Depth

Flat and tonal. Depth comes from the three graphite steps and 1px hairlines; borders, not shadows, define every container. Two shadows exist and both are restrained.

### Shadow Vocabulary
- **Portrait lift** (`box-shadow: 0 24px 60px -30px rgba(0,0,0,.8)`; light: `0 24px 60px -32px rgba(15,23,42,.35)`): the hero portrait card only, a soft drop that seats it above the hero grid.
- **Tooltip** (`box-shadow: 0 12px 30px rgba(0,0,0,.4)`): the floating chart tooltip.

The sticky nav uses a translucent ground (78%) with `saturate(150%) blur(14px)` and gains a hairline bottom border once scrolled.

### Named Rules
**The Hairline Before Shadow Rule.** Separate surfaces with a 1px hairline and a tonal step. Hover strengthens the hairline (`hairline` to `hairline-strong`); it never adds a shadow.

## Shapes

Softly rounded rectangles on a stepped radius scale, larger containers getting larger radii: 6px tags and focus ring, 8px small buttons, nav links, chips and browser chrome, 10px buttons and tooltip, 12px pitch surfaces and the portrait image, 14px cards and chart panels, 18px the portrait card. Circles only for status and legend dots. Inner radii nest: the 18px portrait card holds a 12px image on 10px padding. Borders are always 1px solid hairlines; the browser chrome bar is a hairline tab with three 7px dots and the URL in 11px muted text.

## Components

### Buttons
Quiet, solid, product-like.
- **Shape:** gently rounded (10px; 8px for the 34px small size).
- **Solid (primary):** ink fill, ground-coloured text, 42px high, 18px side padding, 500 weight at 15px, optional 16px leading SVG icon with 8px gap.
- **Line (secondary):** transparent with a `hairline-strong` border and ink text.
- **Hover / Focus / Active:** solid mixes 14% ground into ink; line darkens its border to ink; active nudges down 1px; focus is the global 2px signal outline at 3px offset. Transitions 0.2s.
- **Disabled:** 40% opacity, not-allowed cursor.

### Chips
- **Stack tags:** 12px / 500 muted text in a 1px hairline box, 6px radius, 5px 7px padding; static.
- **Toggle chips and chart tabs:** 13.5px / 600 ink text, transparent fill, 1px hairline, 8px radius. Hover turns the border signal; pressed carries a signal border on a `signal-soft` tint; unpressed filter chips fade to 42% with a strike-through.

### Cards / Containers
- **Work card:** `graphite-soft` fill, 1px hairline, 14px radius, overflow clipped. Screenshot stage on `graphite-raise` inside a hairline browser chrome; body padding 18px 20px 20px (32px on the feature card). Hover strengthens the border, lifts the screenshot 3px over 0.7s, and nudges the arrow icon 2px up-right. The whole card is one link via the title's stretched anchor.
- **Chart panel:** ground fill (raise in light), 1px hairline, 14px radius, no shadow; 22px inner inset; title, caption and mono stats in the head, legend and live tip in the foot.
- **Portrait card:** `graphite-soft`, 18px radius, 10px padding, portrait lift shadow, with a hairline-ruled fact sheet (muted terms, ink values).

### Navigation
Sticky, 62px tall, translucent blurred ground. Brand name in 600 ink at the left; muted 14.5px / 500 links with an 8px-radius `graphite-soft` hover fill; a small solid "Download CV" button; a 34px hairline theme toggle with inline sun and moon SVGs. Under 680px, a two-bar toggle opens a full-width sheet of ink links separated by hairlines.

### Rows
The more-builds list: hairline-ruled rows, ink title, body description, muted tags, trailing arrow; hover fills `graphite-soft` and nudges the arrow.

### Icons
A single inline SVG sprite: 16px, 1.5 stroke, round caps, `currentColor`. Arrows nudge 2px up-right on parent hover.

## Do's and Don'ts

### Do:
- **Do** separate surfaces with 1px hairlines and the ground / soft / raise steps before reaching for a shadow.
- **Do** reserve the signal colour for links, focus, selection, sliders and pressed state.
- **Do** make the primary action an ink-filled button and the secondary a hairline outline button.
- **Do** set every numeral and data readout in Geist Mono with tabular figures.
- **Do** frame product screenshots in the hairline browser chrome unless the image already includes one.
- **Do** keep chart surfaces on the dark pitch with their own data palette in both themes.
- **Do** keep content visible without JavaScript or motion; the only entrance animation is the hero rise (0.9s, `cubic-bezier(.16, 1, .3, 1)`), skipped under reduced motion.
- **Do** define every themed colour as a custom property with a `html[data-theme="light"]` counterpart.

### Don't:
- **Don't** use glow, neon halos, or gradients as a brand fill; gradients are allowed only as drawing and masking tools (hairline grid, scroll-edge fade).
- **Don't** use emoji or icon-font glyphs as icons; use the inline 16px SVG sprite.
- **Don't** fill buttons or large areas with the signal colour.
- **Don't** add uppercase, tracked-out labels or small headings above section titles.
- **Don't** add hover shadows or lift the card itself; strengthen the hairline instead (only the screenshot inside rises 3px).
