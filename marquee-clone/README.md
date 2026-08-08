# Touchline — a study clone of the Marquee product concept

A working, dependency-free re-creation of the idea behind
[Marquee (themarquee.ai)](https://www.themarquee.ai/) — the AI "decision layer" for soccer
scouting and recruitment that raised a $4M seed in July 2026.

> **Disclaimer:** this is an independent **educational study project**. Original design,
> original copy, original code, and 100% synthetic fictional data (players, clubs and
> numbers are generated from a seeded PRNG). It is not affiliated with, endorsed by, or a
> copy of Marquee's actual software or website.

## What it does

Ask scouting questions in plain language and get explained, decision-ready answers —
computed against a configurable "club DNA" (game model, budget, current squad):

- **Shortlists** — `find a tall, fast striker with good ball control under €25m`
- **360° scout reports** — `scout report on <player>` (prose + verdict)
- **Similarity search** — `find players similar to <player>` (cosine over attribute vectors)
- **Market watch** — `what's on the market right now?` (expiring contracts, form spikes, minutes drops)
- **Squad audit** — `where is my squad weakest?`

Every score in the UI expands (click a bar) to show exactly which factors produced it.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | Landing page — the concept, the nine models, the workflows |
| `app.html` | The scouting workspace (query bar, club-DNA sidebar, results feed) |
| `data.js` | Seeded synthetic DB: 120 fictional players + a demo club and squad |
| `engine.js` | Nine scoring modules, rule-based NL query parser, report writer, market watch |
| `app.js` | UI wiring — intents → renderers, expandable explainability |
| `style.css` | Original dark "sports-AI product" design |
| `RESEARCH.md` | The research: how the real Marquee works, with sources |

## Run locally

No build step, no dependencies:

```
python3 -m http.server 8000
```

then open <http://localhost:8000>.
