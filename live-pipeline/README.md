# mini-TRADE360 - a live sports-data pipeline

A working miniature of a sportsbook data feed, modelled on the architecture of LSports'
**TRADE360**: a producer replays recorded World Cup 2026 matches as a live JSON message
feed (fixture metadata, per-minute livescores, keep-alives, settlement), a RabbitMQ topic
exchange routes it, and a trading consumer rebuilds match state, runs an in-play Poisson
win-probability model and publishes 1X2 market updates - with Snapshot API-style recovery
for late joiners and sequence gaps. The model is calibrated on this site's own WC2026 xG
database (`assets/data/argentina/`), and the same pipeline generates the win-probability
timelines that drive the site's live dashboard.

The core is **pure Python stdlib - zero third-party dependencies**. `pika` is only needed
for the optional RabbitMQ mode, `pytest` only for the tests.

## Architecture

```
                        topic exchange "trade"
+----------------+      +-----------------+      +------------------+
| MatchProducer  | ---> |  feed.<fixture> | ---> |  TradeConsumer   |
| replay 0'..FT  |      |                 |      |  MatchState      |
| (recorded xG   |      |                 | <--- |  InPlayModel     |
|  match JSON)   |      | markets.<fixt.> |      |  1X2 pricing     |
+----------------+      +-----------------+      +------------------+
        ^                                                 |
        |            RPC queue "snapshot.<fixture>"       |
        +---- reply: full state + LastMsgSeq <-- request -+
              (late join / MsgSeq gap recovery)
```

Both sides talk to a pluggable `Broker`: `InMemoryBroker` (synchronous, deterministic,
used by tests and timeline builds) or `RabbitBroker` (the same API over a RabbitMQ topic
exchange named `trade`, lazy `pika` import). Routing keys are `feed.<fixture_id>` and
`markets.<fixture_id>`; patterns support a trailing wildcard (`feed.*`) and `#`.

## Message contract

Every message is a TRADE360-style envelope: a `Header` (`Type`, `MsgGuid`, per-fixture
monotonic `MsgSeq`, `ServerTimestamp`, `CreationDate`) plus a `Body` with an `Events`
list. Timestamps are supplied by the producer, so replays are fully deterministic.

| Type | Name | When sent | Key payload fields |
| --- | --- | --- | --- |
| 1 | FixtureMetadataUpdate | Kickoff (`InProgress`) and full time (`Finished`) | `Fixture`: Sport, Venue, Stage, StartDate, Status, Participants |
| 2 | LivescoreUpdate | Every simulated minute on the raw clock, 0..final whistle (`maxMin`) | `Scoreboard` (period, minute, score), `Statistics` (cumulative xG), `Incidents` (that minute's shots/goals with xG, plus any red card) |
| 3 | MarketUpdate | Consumer output, per priced minute up to 90' | `Markets`: 1X2 (90 min) with `Status` (Open/Suspended/Closed) and, when open, `Probability`, fair `Price`, `BookPrice` (5% overround) |
| 31 | KeepAlive | Every 10 simulated minutes | `FixtureId` only (heartbeat) |
| 35 | Settlement | Minute 90 (the 1X2 market clock) | 1X2 bets with `Settlement` 1/0 |

Market state: a book does not quote through a goal. The minute a goal or a red card lands,
the consumer publishes the 1X2 market `Suspended` **with no prices** — quoting a number you
would not accept a bet at is worse than quoting nothing — and reopens it at the new price
the following minute. Settlement closes it. Every timeline row carries the status it was
priced under.

Recovery: the producer is the fixture's snapshot authority and serves the RPC queue
`snapshot.<fixture_id>` from the moment it is constructed. If the consumer sees a
LivescoreUpdate with no local state (late join) or a `MsgSeq` that is not `last_seq + 1`
(gap), it calls the snapshot RPC, rebuilds `MatchState` from the reply, drops anything
the snapshot already covers (`MsgSeq <= LastMsgSeq`), and carries on seamlessly. A skipped
KeepAlive triggers the same recovery, so a gap is caught even when no livescore has arrived
to reveal it.

Redelivery is not a gap. A durable broker with manual acknowledgement *will* resend
messages, so the consumer drops anything it has already handled — by `MsgGuid`, and by
sequence — **before** the gap check. Without that ordering a duplicate looks like a
sequence error and triggers a pointless snapshot round trip.

## The model

One formula drives everything. Per team, the expected goals still to come at minute t:

```
lam_rem(t) = rem(t) * ((1 - w) * lam_prematch + w * 90 * pace) * adj
```

where `pace = xG created in the last 15 minutes / 15`, `rem(t)` is the share of a match's
scoring still ahead, and `adj` holds the multiplicative corrections for score state and red
cards. The two `lam_rem` values plus the current score feed a Poisson grid (0..10 goals per
side, tail renormalized, Dixon-Coles low-score correction) that buckets every final score
into P(home)/P(draw)/P(away), fair odds and 5%-margin book prices.

Every one of those pieces is **fit, not chosen** — and three of them exist because the v2
model was measurably wrong:

| Piece | v2 | v3 | Why |
| --- | --- | --- | --- |
| `rem(t)` | `(90 - t) / 90` | empirical profile | Football does not score evenly. At half time the linear clock says 50% of the scoring is left; the data says **57%**. |
| `w` | 0.35 | **0.05** | 15-minute xG is a noisy signal, and most of what it appears to measure is score state, not form. |
| score state | — | `x exp(+0.25)` trailing, `x exp(-0.05)` leading | The real effect the momentum term was picking up: teams shoot more because they are **losing**, not because they are hot. Biggest single gain. |
| `rho` (Dixon-Coles) | — | +0.05 | Reweights only the four cells where both sides score at most once. The fitted sign is positive, i.e. slightly *fewer* low-score draws — this model never needed its draws inflated. |
| red cards | — | hook, left neutral | See the negative result below. |

**Two honest negatives, kept deliberately.** Draw inflation was tried and *hurts* at every
setting — the miscalibration was never in the draws, it was overconfident favourites. And
red-card multipliers are **not fit**, because the corpora cannot support them: the scrapers
record *that* a player was sent off but never *when* (a dismissed player's minutes-played
stays at the full match length — Darwin Nunez, off on 57', still reads 95). Inferring the
minute puts ~98% of cards at the final whistle where they change nothing, so the pipeline
carries the incident and the model carries the multiplier, both neutral until a feed
supplies real dismissal minutes.

Pre-match rates come from `calibrate.py`: a Dixon-Coles-lite fit with empirical-Bayes
shrinkage over ALL of the scraped corpora (`corpus.py`: EPL + La Liga 2022-23..2025-26
plus World Cups 2018/2022/2026 — 3,272 matches, 82k shots), one baseline `mu` per
competition, team rates namespaced as `EPL/Arsenal` / `WC/Argentina`, recency-weighted
(`0.8^seasons_ago`) so current form dominates. `lam_home = att_H * def_A / mu * hfa`,
with the home-field boost `hfa ≈ 1.13` fit from league matches and dropped to 1.0 on
neutral World Cup venues. Shrinkage strength k is tuned over {1,2,4,8,16} by holdout
Brier (k = 1 wins). The corpora resolve from sibling clones, `/workspace` clones, or
the vendored copies in `projects/`, so this repo alone can refit end-to-end; with no
corpus found at all calibrate falls back to the 8 argentina match JSONs.

**Two clocks, cleanly separated.** The replay runs on the RAW match clock to the real
final whistle (the file's `maxMin`): a group game with long stoppage ends at 90+7', a
knockout that went the distance at ~121', and every event appears at its true minute.
The 1X2 (90 min) MARKET clock is separate: for calibration and settlement, stoppage
events fold into minute 90 (a 90+4' goal settles the market) while extra-time events
never enter (`model.effective_min(minute, has_extra_time)`). Whether a knockout actually
played extra time is classified from the data — `maxMin` >= 115 (ET always reaches 120';
regulation stoppage tops out ~108), shootout evidence, or the event stream — so a
stoppage-time winner is a regulation result, not extra time. The market settles at the
whistle (or at 90' when ET follows, after which MarketUpdates stop); the timeline keeps
one row per raw minute to the end, converging to the one-hot result at the whistle.

**The protocol matters more than the model.** Three blocks, disjoint in time:

```
inner    2022-23, 2023-24 leagues + WC2018    ratings, while tuning
val      2024-25 leagues + WC2022             chooses EVERY hyper
holdout  2025-26 leagues + WC2026             scored ONCE, at the end
```

v2 tuned its shrinkage strength k on the same holdout it then reported, which flatters the
number. Now nothing is chosen on the holdout: one finished configuration is scored against
it a single time, then the production rates are refit on all data.

Back-test (mean Brier per checkpoint vs the 90-minute outcome, on the 864 held-out matches
— from `assets/data/winprob/model_params.json`):

| Minute | v3 | v2 (w=0.35) | v2 w=0 | Constant base-rate |
| --- | --- | --- | --- | --- |
| 0 | **0.6057** | 0.6176 | 0.6072 | 0.6449 |
| 15 | **0.5804** | 0.6014 | 0.5832 | 0.6449 |
| 30 | **0.5537** | 0.5812 | 0.5587 | 0.6449 |
| 45 | **0.5058** | 0.5252 | 0.5141 | 0.6449 |
| 60 | **0.4394** | 0.4548 | 0.4472 | 0.6449 |
| 75 | **0.3504** | 0.3652 | 0.3625 | 0.6449 |
| 90 | 0.0000 | 0.0000 | 0.0000 | 0.6449 |
| **mean (live)** | **0.5059** | 0.5242 | 0.5121 | 0.6449 |
| **mean log loss** | **0.8549** | 0.8918 | 0.8658 | — |
| **calibration error (ECE)** | **0.0052** | 0.0548 | — | — |

v3 wins at every checkpoint and in every competition (EPL −0.014, La Liga −0.025, WC
−0.009). It also fixes something the Brier score barely shows: **v2 was overconfident**.
Pooled over minutes 15–75, matches v2 priced at 85% actually won 72% of the time; v3's
same bucket wins 87%. That is the ECE column, and it is the difference between a number you
can trade on and a number that merely ranks well.

The v2 curiosity that started all this is still in the table — plain w=0 beat the w=0.35
momentum blend — and v3 explains it rather than papering over it: the momentum term was a
noisy proxy for score state, so replacing it with the real thing beats both.

## Run it

Everything below except the rabbit rows needs nothing installed. From the repo root:

| What | Command |
| --- | --- |
| List available matches | `python3 live-pipeline/run_demo.py --list` |
| Replay a match, live pricing (~9 s) | `python3 live-pipeline/run_demo.py --match 2026_06_17_Argentina_vs_Algeria --speed 600` |
| Late-join snapshot recovery demo | `python3 live-pipeline/run_demo.py --match 2026_07_04_1J_vs_2H --speed 600 --late-join 60` |
| Same, over real RabbitMQ | `python3 live-pipeline/run_demo.py --match 2026_06_17_Argentina_vs_Algeria --speed 600 --broker rabbit` |
| Refit model params | `python3 live-pipeline/tradepipe/calibrate.py` |
| Regenerate site timelines | `python3 live-pipeline/tradepipe/build_timelines.py` |
| Regenerate the page's message feeds | `python3 live-pipeline/tradepipe/dump_feed.py` |
| Multi-fixture consumer | one `feed.*` binding — see `MultiFixtureConsumer` in `tradepipe/consumer.py` |
| Tests | `python3 -m pytest live-pipeline/tests -q` |
| Tests incl. RabbitMQ | `TRADEPIPE_RABBIT_URL=amqp://guest:guest@localhost:5672/%2F python3 -m pytest live-pipeline/tests -q` |

`--speed` is simulated minutes per real minute (60 = ~1 s per minute, 600 = whole match
in ~9 s). `--late-join N` attaches the consumer only from minute N, forcing a MsgSeq gap
and a snapshot recovery. `--rabbit-url` overrides the default
`amqp://guest:guest@localhost:5672/%2F`.

Rabbit mode needs a local broker and the one optional dependency:

```
docker run -d -p 5672:5672 rabbitmq:3
pip install pika
```

Regeneration order after new match data: `calibrate.py` (rewrites
`assets/data/winprob/model_params.json`, and ships `winprob_params.js` + `winprob_model.js`
into every dashboard), then `build_timelines.py` (rewrites
`assets/data/winprob/<match_id>.json` + `index.json` for the dashboard). CI checks that a
timeline rebuild is byte-identical to what is committed.

## Files

| File | Purpose |
| --- | --- |
| `run_demo.py` | CLI: replay one match as a live feed and price it (`--list`, `--match`, `--speed`, `--broker`, `--late-join`) |
| `requirements.txt` | Documents that the core has no deps; `pika` optional for rabbit mode |
| `tradepipe/messages.py` | TRADE360-style envelope + builders for MsgTypes 1/2/3/31/35 |
| `tradepipe/broker.py` | `Broker` API, synchronous `InMemoryBroker`, `RabbitBroker` (topic exchange `trade`, RPC) |
| `tradepipe/producer.py` | `MatchProducer`: deterministic raw-clock replay to the real final whistle, snapshot authority |
| `tradepipe/snapshot.py` | Snapshot payload contract shared by producer (build) and consumer (parse) |
| `tradepipe/state.py` | `MatchState`: rebuilds score/xG/incidents from the feed, MsgSeq gap detection |
| `tradepipe/consumer.py` | `TradeConsumer`: pricing, MarketUpdate publishing, market suspension, dedup, snapshot recovery, timeline recording; `MultiFixtureConsumer` fans one subscription out across fixtures |
| `tradepipe/model.py` | `InPlayModel`: `lam_remaining`, Poisson grid, fair odds, book prices |
| `tradepipe/corpus.py` | Loads + normalizes the scraped corpora (EPL, La Liga, WC 2018/2022/2026) |
| `tradepipe/calibrate.py` | Fits per-competition mu, namespaced att/def rates, hfa; tunes k by holdout Brier; writes `model_params.json` + dashboard `winprob_params.js` files |
| `tradepipe/build_timelines.py` | Replays every match through the pipeline, writes `assets/data/winprob/*` |
| `tradepipe/dump_feed.py` | Writes each match's real message envelopes to `assets/data/pipeline/` for the page's live console |
| `web/winprob_model.js` | The browser port of `model.py` — one file, shipped by `calibrate.py` to every dashboard |
| `web/feed_replay.js` | Browser-side consumer: `MatchState` + dispatch + gap detection + snapshot recovery, pricing through `winprob_model.js` |
| `tests/test_model.py` | Model unit tests (clock profile, score state, Dixon-Coles, red cards, horizon) |
| `tests/test_corpus.py` | Corpus loader tests (synthetic matches_detail fixtures) |
| `tests/test_broker.py` | Transport tests — AMQP routing semantics, dispatch order, RPC |
| `tests/test_pipeline.py` | End-to-end pipeline tests (replay, recovery, settlement, suspension, duplicates, multi-fixture) + v3 params shape |
| `tests/test_rabbit.py` | RabbitMQ integration tests (skipped unless `TRADEPIPE_RABBIT_URL` is set) |

## What a production version would change

This is a miniature, and it is worth being explicit about where the edges are. Everything
in the "shipped" column is in this repo and tested; the rest is scope, not oversight.

| Concern | Shipped here | A production feed would add |
| --- | --- | --- |
| Delivery | Durable exchange and queues, persistent messages, publisher confirms, manual acks, `MsgGuid` + sequence dedup | Dead-letter queues with replay tooling, consumer groups per market type, backpressure |
| Recovery | Snapshot RPC on late join, sequence gap, or skipped KeepAlive | Snapshot cadence and TTLs, a bounded replay buffer so small gaps skip the RPC entirely |
| Market state | Open / Suspended / Closed, suspend on goal or dismissal | Per-selection suspension, latency-aware auto-suspend, trader override, price-change throttling |
| Scale | `MultiFixtureConsumer` over one `feed.*` binding, one process | Partition by fixture across workers, shared rating cache, horizontal consumers on a durable named queue |
| Markets | 1X2 (90 min) | Over/Under, AH, correct score, HT/FT — the same Poisson grid already contains all of them |
| Model | Fit offline, shipped as JSON + a matching JS port | Online recalibration, drift monitoring, per-league priors, injury/lineup features |
| Ops | GitHub Actions: unit, end-to-end, RabbitMQ integration, reproducible-timeline check | Metrics on gap rate, snapshot latency, price staleness; alerting on stale fixtures |

## Why this project

- **Deterministic replay of a real feed shape.** Recorded matches become a reproducible
  message stream - fixed timestamps, monotonic MsgSeq - so every pipeline behaviour
  (ordering, gaps, settlement) can be tested exactly, the way feed replays are used to
  debug production trading systems.
- **Sequence-gap detection and snapshot recovery.** The consumer tracks MsgSeq, detects
  gaps, and rebuilds state from a request/reply snapshot channel - the same
  push-feed-plus-Snapshot-API pattern real odds feeds use to keep consumers consistent -
  while telling a genuine gap apart from an ordinary redelivery.
- **Market pricing, not just data plumbing.** The consumer turns raw livescores into an
  actual 1X2 market - probabilities, fair odds, margined book prices, and a suspend/reopen
  lifecycle around goals - with a calibrated model and an honest back-test, including the
  90-minute market clock conventions real settlement depends on.
- **A model that was measured, corrected, and re-measured.** The v2 fit was beaten by its
  own no-momentum baseline and was badly overconfident (85% quotes won 72% of the time).
  Rather than ship the nicer story, the protocol was fixed, the failure diagnosed
  (score state, not momentum) and the model rebuilt: ECE 0.055 -> 0.005 on a holdout that
  is scored exactly once. Two things that did NOT work - draw inflation and red-card
  fitting - are documented as negatives instead of quietly dropped.
- **Explicit message contracts over a real broker.** Typed envelopes, routing keys, a
  topic exchange and an RPC queue, behind a transport abstraction that runs identically
  in-memory (tests) and on RabbitMQ (deployment-shaped).
- **The feed is visible, not just described.** The page's console replays the producer's
  actual envelopes through a consumer running in the browser - state rebuilt from the
  stream, priced by the same model - and a button drops six messages so you can watch the
  gap get detected and repaired. The recovered prices are identical to the uninterrupted
  ones, which is exactly the guarantee a Snapshot API is for.

> Built a real-time sports data pipeline mirroring TRADE360 architecture - RabbitMQ
> producer/consumer with snapshot recovery, TRADE-style message contracts, and an
> in-play Poisson win-probability model calibrated on World Cup xG data, powering
> live dashboards.
