# Marquee (themarquee.ai) — platform research

> Research notes compiled 2026-08-08 from public press coverage. Everything below is
> paraphrased from public sources (linked at the bottom). The demo in this folder is an
> **independent, educational re-creation of the product concept** with original design and
> code. It is not affiliated with, endorsed by, or a copy of Marquee's actual site or
> software. Player data comes from public datasets and is used for non-commercial research
> and demonstration only.

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
| NL query → ranked shortlist | Rule-based parser over **16,161 real players**, scored and ranked in `engine.js` |
| 360° scout report | Per-player prose: performance, physical, technical, trajectory, synergy vs. a real squad, ending in a verdict |
| Club DNA / tactical fit | Pick any of **638 real clubs** as "your" squad; game model reweights every score |
| Squad synergy | Computed against that club's actual squad — line quality, incumbent competition, missing left foot |
| Market watch | **Real** signals: contract expiries and valuations, plus three-season minutes and output trends |
| Market value | Real Transfermarkt fee vs. your budget, with contract-expiry leverage factored in |
| Nine models | Nine named modules, eight scoring and one writing, each exposing its reasoning |
| "Explainability" | Every score expands to the factors — and ultimately the match stats — that produced it |

## 6. The data pipeline (`build_players.py`)

Three public sources, combined so that **game-style attribute priors get updated by observed
match statistics** — the same shape as "scout judgement, corrected by data":

| Layer | Source | Scale | Role |
| --- | --- | --- | --- |
| Attribute prior | EA FC 24 ratings | 15,846 players · 654 clubs · 155 nations | Global baseline, incl. leagues with no public event data |
| League map | FIFA 22 dataset | 55 leagues | club → league, joined by player name |
| Performance | FBref Big-5 advanced season stats | 8,117 player-seasons, 2022/23–2024/25 | Re-derives attributes from real output |
| Valuation & contracts | Published Transfermarkt dump (values to Sept 2025) | 92,671 profiles · 33,590 values · 38,666 contract dates | Real fees, contract expiry, height, date of birth, citizenship |
| Global career | Same dump: appearances, injuries, valuation history | 1.88M appearance rows · 707 competitions · 143k injury records | Availability and momentum **worldwide**, not just the big 5 |

**How the update works.** For every player matched to FBref, each attribute is re-estimated as a
**percentile rank against positional peers** on the relevant per-90 metrics — finishing from npxG
and goals-over-expected, creativity from xAG and key passes, dribbling from take-ons and
progressive carries, defending from a 50/50 blend of action volume and duel-success rate. The
estimate is then blended over the prior with **minutes-weighted (empirical-Bayes) shrinkage**,
`w = minutes / (minutes + 900)`, so a 200-minute sample barely moves the prior while a full
season dominates it.

Every player carries a confidence tier, surfaced as a badge in the UI:

- **Verified** (1,575) — a full Big-5 season behind the ratings
- **Partial** (784) — matched, but a small minutes sample
- **Baseline** (13,802) — EA FC 24 prior only; the league has no public event data

## 7. Known limitations — read before trusting a number

- **The freshest complete season is 2024/25.** The FBref mirror used here is archived and froze
  about five games into 2025/26, so that partial season is excluded rather than shipped as form.
- **Non-Big-5 players are a 2023/24 snapshot.** Clubs and ages for baseline-tier players come
  from EA FC 24; some will have transferred since.
- **Appearances are global; event data is not.** Appearance counts, injuries and valuations cover
  every competition, so availability and momentum are real for an MLS or Championship player. But
  *attribute* ratings still only get updated where FBref event data exists — the two must not be
  confused.
- **The appearance table's `minutes_played` column is not minutes.** It is minutes *per goal*, and
  null whenever a player didn't score. Workload here is therefore measured in appearances and share
  of matchday squads; the minutes column is ignored entirely.
- **Event data can't see everything.** Positioning, composure and off-ball movement aren't
  measurable from event data — those attributes stay at their prior. Marquee buys this gap with
  SkillCorner tracking data; this clone has no equivalent.
- **Defensive volume misreads elite centre-backs.** Players who prevent situations record fewer
  actions. Blending in duel-success rate helps, but a positional CB can still under-rate.
- **Joins are name-based.** Players sharing a name are separated by club, position and age
  agreement, but roughly 1.8% of names are shared and some matches will be wrong.
- **Market values cover 64% of the database.** 10,307 of 16,163 players carry a real Transfermarkt
  valuation and 9,286 a contract expiry. The rest show no fee at all and the market model returns a
  neutral score rather than guessing — a missing value is never imputed.
- **Valuations are a single Sept 2025 snapshot.** They are Transfermarkt's community-driven estimates,
  not transfer fees, and they are not re-dated per season.
- **The "models" are arithmetic, not learned.** Percentiles and weighted averages standing in for
  transformers over match sequences.

Everything is static HTML/CSS/JS — no backend, no build step, no runtime dependencies.

## 8. Sources

- [Marquee raises $6.5M — GlobeNewswire press release](https://www.globenewswire.com/news-release/2026/07/30/3336140/0/en/marquee-raises-6-5-million-to-scale-ai-decision-layer-across-global-sports.html)
- [Yahoo Finance republication of the press release](https://finance.yahoo.com/technology/ai/articles/marquee-raises-6-5-million-130100497.html)
- [CTech / Calcalist — "Starting from an Arsenal fan group, Marquee says it's the 'Claude Code' for sports recruitment"](https://www.calcalistech.com/ctechnews/article/kbfidxotv)
- [Ynet — pre-seed coverage: cutting losses on failed transfers](https://www.ynetnews.com/business/article/hjkc8rwowe)
- [Jewish News — "From Arsenal to AI"](https://www.jewishnews.co.uk/from-arsenal-to-ai-the-israeli-startup-transforming-how-clubs-sign-players/)
- [Dealroom note on the seed round](https://app.dealroom.co/news/note/marquee-raises-6-5m-seed-to-build-ai-decision-layer-for-pro-sports)
- [Marquee's own site](https://www.themarquee.ai/) (not directly reachable from this environment's network; described via search snippets)
