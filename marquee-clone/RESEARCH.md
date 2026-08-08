# Marquee (themarquee.ai) — platform research

> Research notes compiled 2026-08-08 from public press coverage. Everything below is
> paraphrased from public sources (linked at the bottom). The `marquee-clone/` demo in this
> folder is an **independent, educational re-creation of the product concept** with original
> design, copy, and synthetic data — it is not affiliated with, endorsed by, or a copy of
> Marquee's actual site or software.

## 1. Company snapshot

| | |
| --- | --- |
| HQ | Tel Aviv, Israel (opening offices in the U.S. and U.K.) |
| Founded | 2025 |
| Founders | Dean Bracha (CEO), Dror Rosenfeld (CPO), Tal Darchi (CDO), Jonathan Hazut (CTO) |
| Funding | $4M seed (Jul 2026) led by AnD Ventures, with Axel Springer SE, Welltech Ventures, Apex Capital, 97212 Ventures, JCP — on top of a ~$2.5M pre-seed also led by AnD. Total ≈ $6.5M |
| Traction | 20+ professional clubs & federations, incl. teams in the Premier League, Serie A, and MLS |
| Data partners | SkillCorner (tracking / physical data), Gradient Sports |
| Roadmap | Basketball platform in development; new capital goes to R&D and AI/engineering/data-science hiring |

Origin story: three of the four founders are Arsenal supporters; Bracha ran an Arsenal fan
community (7,000+ members) where he wrote match reviews and transfer analysis — that habit of
turning raw matches into written, opinionated analysis is essentially what the product
automates. The pitch line they use is that Marquee is a **"Claude Code for recruitment
teams."**

## 2. What the product is

Marquee is **not a new data provider**. Clubs already drown in data — event data, tracking
data, video, medical, contract and financial info, scouting notes — scattered across vendor
platforms and internal systems. Marquee positions itself as the **AI-native intelligence /
decision layer** that sits *on top* of all of that:

1. **Unify** — connect the club's existing external feeds (e.g. SkillCorner, Gradient
   Sports, event-data vendors) and internal systems into one layer.
2. **Contextualize** — encode the club's own "DNA": playing philosophy, squad composition,
   budget constraints, league context, objectives.
3. **Answer** — let staff query everything in plain language and get back decision-ready,
   *explainable* outputs in seconds instead of weeks of manual work. The claim is that it
   automates roughly **70% of manual recruitment workflows**.

## 3. How it works under the hood

- **Nine proprietary AI/ML models** with football domain expertise built in, sitting on top
  of the club's competition data. Marketed as "the only LLM purpose-built for football."
- **Players as high-dimensional vectors** — each player is embedded from their data, so
  similarity search ("find me another X") is a nearest-neighbour problem in embedding space.
- **Transformer models trained on hundreds of thousands of match sequences** — used to
  simulate how a player would combine with a specific squad ("team chemistry" / synergy) and
  to compute **tactical fit** against a system, not just raw quality.
- **Natural-language interface on top** — an LLM layer translates a scout's question into
  queries over the models and writes the answer back as prose with the reasoning laid out
  (explainability is a stated design goal — recommendations come with the "why").

## 4. The core user workflows

1. **Shortlist building** — ask in plain language, e.g. *"find a tall, fast striker with
   good ball control"* (their canonical example), plus constraints (budget, age, league).
   Returns a **ranked shortlist** with fit scores and reasoning.
2. **360° scout reports** — ask about any player and get the full picture in seconds:
   on-pitch performance, off-pitch profile, financials, and a **synergy score against your
   current squad**, each dimension scored against the club's DNA.
3. **Squad planning / tactical analysis** — break down your own team and upcoming opponents:
   strengths, weaknesses, positional depth, where the squad ages out.
4. **Market intelligence, 24/7** — the platform continuously watches the market: contract
   expiries, financial distress at selling clubs, shifting minutes, emerging form — surfacing
   "hidden gems" and windows of opportunity before they're obvious.

The economic wedge: failed transfers burn billions across football every year; a layer that
raises the hit rate of recruitment decisions pays for itself on a single avoided mistake.

## 5. What the clone in this folder re-creates

| Marquee concept | Clone implementation |
| --- | --- |
| NL query → ranked shortlist | Client-side query parser over a synthetic player DB (`players.js`), scoring + ranking in `app.js` |
| 360° scout report | Generated report per player: performance, physical, financial, synergy vs. a demo squad, written as prose from templates |
| Squad DNA / tactical fit | A configurable "club profile" (style, budget, league) that reweights the ranking |
| Market watch | A feed of synthetic signals (expiring contracts, minutes trends, form spikes) recomputed from the dataset |
| Nine models | Nine named scoring modules in the demo engine, each contributing an explainable sub-score |
| "Explainability" | Every score in the UI expands to show which factors moved it |

Everything is static HTML/CSS/JS with synthetic data — no backend, no real player data, no
external dependencies, matching the conventions of the rest of this repo.

## 6. Sources

- [Marquee raises $6.5M — GlobeNewswire press release](https://www.globenewswire.com/news-release/2026/07/30/3336140/0/en/marquee-raises-6-5-million-to-scale-ai-decision-layer-across-global-sports.html)
- [Yahoo Finance republication of the press release](https://finance.yahoo.com/technology/ai/articles/marquee-raises-6-5-million-130100497.html)
- [CTech / Calcalist — "Starting from an Arsenal fan group, Marquee says it's the 'Claude Code' for sports recruitment"](https://www.calcalistech.com/ctechnews/article/kbfidxotv)
- [Ynet — pre-seed coverage: cutting losses on failed transfers](https://www.ynetnews.com/business/article/hjkc8rwowe)
- [Jewish News — "From Arsenal to AI"](https://www.jewishnews.co.uk/from-arsenal-to-ai-the-israeli-startup-transforming-how-clubs-sign-players/)
- [Dealroom note on the seed round](https://app.dealroom.co/news/note/marquee-raises-6-5m-seed-to-build-ai-decision-layer-for-pro-sports)
- [Marquee's own site](https://www.themarquee.ai/) (not directly reachable from this environment's network; described via search snippets)
