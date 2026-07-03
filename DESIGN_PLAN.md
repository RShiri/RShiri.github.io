# Design plan: make rshiri.github.io feel less generic

## The diagnosis

The strongest thing on this site is the thing no template has: the hand-built
interactive analytics (the Yamal shot map, the take-on map, the Argentina-Algeria
match centre with pass-by-pass goal replays). That work is distinctive.

Everything *around* it is the 2024-25 default portfolio look, and that's what
reads as generic:

| Generic marker | Where it lives today |
| --- | --- |
| Indigo→cyan gradient accent (`#4f46e5` → `#06b6d4`) | `--grad` in `styles.css:15`, buttons, monogram, gradient hero text |
| Gradient-clipped headline text | `.grad` on the hero h1 |
| Inter + Space Grotesk pairing | font link in `index.html:23` |
| "Hi, I'm X. I turn Y into Z." hero formula | hero copy, `index.html:58` |
| Pill-shaped everything (buttons, tags, "Open to work" pulsing dot) | `.btn`, `.tag`, `.pill` |
| Uppercase kicker + big heading + muted subtitle per section | `.kicker` pattern |
| Symmetric 3-card project grid with hover-lift + image zoom | `.projects` / `.project:hover` |
| Radial gradient blob background | `.hero` background |
| Emoji as UI (☀️ 🌙 ⚽🏀🏎️ ✉︎) | theme toggle, hero stats, contact button |
| Section titles like "Let's build something." | contact section |

**The strategy is not "add more decoration" — it's to let the sports-analytics
identity that already exists inside the dark viz panels take over the whole
page.** Design the site like a match-day programme / broadcast stats package,
not like a SaaS landing page. Every choice below follows that one idea.

---

## Phase 1 — Identity: palette + type (the 80% of "generic")

**Goal: no visitor can mistake this for a template within the first second.**

1. **Kill the indigo→cyan gradient.** One signature accent colour, used flat.
   Candidates that fit the broadcast/pitch world and stand out in portfolios:
   - Volt / highlighter green (`#c8f542`-ish) on the dark navy — reads
     "pitch + broadcast overlay", pairs beautifully with the existing
     `#0f1626` panel colour.
   - Alternative: warm signal orange (`#ff5c1f`-ish) — heatmap/Opta energy.
   Pick ONE. Accent is for links, active states, key numbers. Buttons become
   flat (accent fill or 1px outline), squared-off (4–6px radius, not 999px).
2. **Gradient text → plain ink.** The hero headline gets its impact from the
   new typeface and size, not from a rainbow fill.
3. **Replace the font pairing.** Inter + Space Grotesk is the default of
   thousands of AI-generated portfolios. New system, all on Google Fonts:
   - Display / headlines: **Archivo** (Expanded weights) or
     **Barlow Condensed** — scoreboard/jersey energy without being a novelty
     font.
   - Numbers, labels, legends, kickers: **IBM Plex Mono** or
     **Space Mono** with `font-variant-numeric: tabular-nums` — everything
     that displays a stat should look like telemetry.
   - Body: keep a quiet workhorse (Inter is fine *as body only*, or swap to
     **Public Sans**) — body text is not where generic lives.
4. **Dark-first for real.** Dark is already the default; commit to it. The
   light theme keeps working but becomes the variant, tuned after the dark
   identity is settled.
5. **Rebuild the monogram/favicon** in the new identity: flat accent square or
   a tiny scoreboard tile ("RS 1–0") instead of the gradient rounded square.

Files touched: `styles.css` (tokens at the top do most of the work),
`index.html` (font link), `assets/favicon.svg`, `main.js` (theme icon).

## Phase 2 — Hero: from elevator pitch to player card

**Goal: the first screen demonstrates the craft instead of describing it.**

1. **Drop the "Hi, I'm Ram / I turn sports data into insight" formula.**
   Present yourself the way your own dashboards present players — a
   scouting-card hero:
   - Name set huge in the display face, like a match-graphic lower third.
   - A mono "position line": `DATA ENGINEER · B.Sc. YR 3 · SPORTS ANALYTICS`.
   - A one-sentence editorial claim in plain language underneath.
2. **Hero stats become a scoreboard strip**, not three pill factoids:
   mono type, tabular numbers, thin rules between cells — visually the same
   language as the `viz-stats` blocks further down. Replace the ⚽🏀🏎️ emoji
   cell with real numbers (shots plotted, take-ons mapped, matches in the
   WC pipeline — data you actually have in `assets/data/`).
3. **Portrait treatment:** swap the rounded-rect glamour shot for a framed
   "squad photo" card — flat border, mono caption bar underneath
   (`SHIRI · #7 · OPEN TO WORK`). The pulsing green "open to work" pill folds
   into that caption and stops being a floating LinkedIn-style badge.
4. **Background:** delete the radial gradient blobs. If the hero needs
   texture, use the pitch-line motif — a faint corner arc / centre circle in
   1px line work, same stroke style as the SVG pitches below.

Files touched: `index.html` (hero markup), `styles.css`.

## Phase 3 — A section language of its own

**Goal: the connective tissue between visualizations uses the same visual
grammar as the visualizations.**

1. **Kickers → mono data labels.** Replace the uppercase indigo kicker with a
   mono label with an index, rule-aligned: `01 / ABOUT` — like an axis label,
   in muted ink with a thin rule running to the margin.
2. **Extend the pitch-line motif** as the site's border system: sections are
   separated by the same `rgba(255,255,255,.18)` 1–2px line work the pitches
   use, instead of soft `--bg-soft` background bands.
3. **About → "Scouting report".** Keep the copy but reframe the facts card as
   a player-profile table (mono keys, tabular values). The skills cloud of 14
   pills becomes a compact typed list grouped by role
   (`LANGUAGES / Python · Java · SQL`, `STACK / Pandas · Streamlit · Plotly`,
   ...) — grouped text reads senior; a pill cloud reads template.
4. **Retitle sections in the analyst voice** — sparingly, so it doesn't tip
   into gimmick: "About" → "Scouting report", "Projects" → "Selected work" or
   "Fixtures", Contact headline loses "Let's build something."

Files touched: `index.html`, `styles.css`.

## Phase 4 — Projects: from card grid to fixture list

**Goal: kill the most template-shaped component on the page.**

1. Replace the symmetric 3-card grid with **full-width editorial rows**:
   screenshot on one side, content on the other, alternating. Each row gets:
   - A mono index (`P-01`) and season-style date range.
   - One or two **real stat callouts** per project (fixtures covered, shots
     modelled, update cadence) in scoreboard type — specifics are the
     single strongest anti-generic signal.
   - Tags as plain mono text separated by middle dots, not pill chips.
2. **Remove hover-lift + image-zoom** (`translateY(-5px)` / `scale(1.04)`)
   — the tell of a template card. Hover states become underlines and accent
   colour shifts.
3. Screenshot frames get the flat 1px border + caption-bar treatment from the
   hero portrait, so photography/screenshots share one system.

Files touched: `index.html`, `styles.css`.

## Phase 5 — Motion & micro-interactions (one signature, not ten effects)

**Goal: motion that could only belong to this site.**

1. **Count-up on stat numerals** (hero strip, viz stats) when they scroll into
   view — cheap to build, and makes the whole page feel like a live dashboard.
   Respect `prefers-reduced-motion` (the CSS guard already exists).
2. **Scroll-draw the pitch lines**: the SVG pitch outlines stroke themselves
   in as each viz panel enters the viewport (`stroke-dasharray` animation).
3. **Nav scrollspy indicator** styled as a match-clock tick / accent underline
   rather than a colour swap.
4. Delete generic effects that fight the new tone: button `translateY`
   hovers, card lifts. Keep the tooltip system — it's good.

Files touched: `main.js`, `styles.css`.

## Phase 6 — Voice, depth, and finish

1. **Copy pass in the analyst voice** — plain, specific, confident. Concrete
   numbers over adjectives everywhere ("388 take-ons mapped" is already the
   best sentence on the site; make everything sound like that).
2. **Method notes**: 2–3 sentences under each viz — where the data comes
   from, how the xG model estimates, known limitations. Showing your working
   is what separates an analyst's site from a themed template.
3. **Replace emoji UI** with tiny inline SVG icons (sun/moon toggle, mail)
   drawn in the same 1.5px stroke style as the pitch lines.
4. **Regenerate `og.png`** in the new identity — a scoreboard-style share
   card (name, position line, a mini shot map). Most first impressions happen
   in a link preview.
5. **Housekeeping while in there:** set the real LinkedIn URL
   (`main.js` `LINKEDIN_URL`), self-host the two font families to drop the
   Google Fonts round-trip, re-capture the three project screenshots on the
   new dark theme.

---

## Order of attack

| Step | Scope | Impact | Effort |
| --- | --- | --- | --- |
| 1 | Palette + type tokens (Phase 1) | Huge — kills 80% of the generic feel | Small: mostly `:root` variables + font link |
| 2 | Hero rebuild (Phase 2) | Huge — it's the first screen | Medium |
| 3 | Section language + projects (Phases 3–4) | High | Medium |
| 4 | Motion signature (Phase 5) | Medium | Small |
| 5 | Voice, OG image, icons, housekeeping (Phase 6) | Medium | Small |

Each step ships independently — the site never has to be broken in between.

## Decisions to make before step 1

1. **Accent colour:** volt green vs. signal orange (see Phase 1). Volt green
   is the stronger "pitch" story; orange is warmer and rarer in portfolios.
2. **Display face:** Archivo Expanded (modern broadcast) vs. Barlow Condensed
   (classic scoreboard). Both free; Archivo is the safer default.
3. **How far to push the sports framing** in copy ("Scouting report",
   caption-bar `#7`): full lean-in vs. keep section names conventional and
   let the visuals carry it. Recommended: lean in for labels/captions, keep
   navigation labels conventional (About / Projects / Contact) so recruiters
   never get lost.
