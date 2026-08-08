# Touchline — a study clone of the Marquee product concept

A working, dependency-free re-creation of the idea behind
[Marquee (themarquee.ai)](https://www.themarquee.ai/) — the AI "decision layer" for soccer
scouting and recruitment that raised a $4M seed in July 2026.

Built on **16,161 real players** across **59 competitions** and **707 clubs**, with ratings
derived from real match statistics wherever public event data exists.

> **Disclaimer:** an independent **educational study project**. Original design, copy and code.
> Not affiliated with, endorsed by, or a copy of Marquee's software or website. Player data
> comes from public datasets (EA FC 24 ratings, FBref match statistics, FIFA 22 league mapping)
> and is used here for non-commercial research and demonstration only.

## What it does

Ask scouting questions in plain language and get explained, decision-ready answers — computed
against a real club's squad and game model:

- **Shortlists** — `find a tall, fast striker with good ball control`
- **360° scout reports** — `scout report on <player>` (prose + pursue/monitor/pass verdict)
- **Similarity search** — `find players similar to <player>` (cosine over attribute vectors)
- **Market watch** — `what's on the market right now?` (real minutes/output trends)
- **Squad audit** — `where is my squad weakest?`

Pick any of 638 clubs as "your" club in the sidebar; synergy, squad audits and every fit score
recompute against that actual squad. Click any score bar to see the factors behind it.

## The data pipeline

`build_players.py` combines three public sources so that **game-style attribute priors get
updated by observed match statistics**:

| Layer | Source | Scale |
| --- | --- | --- |
| Attribute prior (global) | EA FC 24 ratings | 15,846 players · 654 clubs · 155 nations |
| League map | FIFA 22 dataset | 55 leagues |
| Performance update | FBref Big-5 season stats, 2022/23–2024/25 | 8,117 player-seasons |

Attributes for matched players are re-derived as **percentile ranks against positional peers**
(finishing from npxG and goals-over-expected, creativity from xAG and key passes, and so on),
then blended over the prior with **minutes-weighted shrinkage** so small samples don't dominate.

Each player is badged by data confidence: **verified** (1,575), **partial** (784), or
**baseline** (13,802 — no public event data for their league).

Regenerate the database with:

```
python3 build_players.py     # needs pandas, numpy, pyreadr; caches downloads in .cache/
```

Read `RESEARCH.md` for the method in full, the research on how the real Marquee works, and an
honest list of **known limitations** — including what event data simply cannot measure.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | Landing page — the concept, the nine models, the workflows |
| `app.html` | The scouting workspace |
| `build_players.py` | Data pipeline that generates `players.json` |
| `players.json` | The player database (2.6 MB, columnar) |
| `data.js` | Loads and decodes the database; club selection |
| `engine.js` | Nine modules, NL query parser, report writer, market watch |
| `app.js` | UI wiring — intents → renderers, expandable explainability |
| `style.css` | Original dark "sports-AI product" design |
| `RESEARCH.md` | Research, method, sources and limitations |

## Run locally

Needs a real HTTP server (the app fetches `players.json`):

```
python3 -m http.server 8000
```

then open <http://localhost:8000>.
