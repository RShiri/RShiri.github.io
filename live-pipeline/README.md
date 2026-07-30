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
| 2 | LivescoreUpdate | Every simulated minute, 0..90 (0..120 when a knockout goes to extra time) | `Scoreboard` (period, minute, score), `Statistics` (cumulative xG), `Incidents` (that minute's shots/goals with xG) |
| 3 | MarketUpdate | Consumer output, per priced minute up to 90' | `Markets`: 1X2 (90 min) with `Probability`, fair `Price`, `BookPrice` (5% overround) |
| 31 | KeepAlive | Every 10 simulated minutes | `FixtureId` only (heartbeat) |
| 35 | Settlement | Minute 90 (the 1X2 market clock) | 1X2 bets with `Settlement` 1/0 |

Recovery: the producer is the fixture's snapshot authority and serves the RPC queue
`snapshot.<fixture_id>` from the moment it is constructed. If the consumer sees a
LivescoreUpdate with no local state (late join) or a `MsgSeq` that is not `last_seq + 1`
(gap), it calls the snapshot RPC, rebuilds `MatchState` from the reply, drops anything
the snapshot already covers (`MsgSeq <= LastMsgSeq`), and carries on seamlessly.

## The model

One formula drives everything. Per team, the expected goals still to come at minute t:

```
lam_rem(t) = ((90 - t) / 90) * ((1 - w) * lam_prematch + w * 90 * pace)
```

where `pace = xG created in the last 15 minutes / 15` and `w = 0.35` blends pre-match
expectation with live momentum (floored so a dominated team never drops to zero). The two
`lam_rem` values plus the current score feed an independent-Poisson grid (0..10 goals per
side, tail renormalized) that buckets every final score into P(home)/P(draw)/P(away),
fair odds and 5%-margin book prices.

Pre-match rates come from `calibrate.py`: a Dixon-Coles-lite fit with empirical-Bayes
shrinkage over ALL of the scraped corpora (`corpus.py`: EPL + La Liga 2022-23..2025-26
plus World Cups 2018/2022/2026 — 3,272 matches, 82k shots), one baseline `mu` per
competition, team rates namespaced as `EPL/Arsenal` / `WC/Argentina`, recency-weighted
(`0.8^seasons_ago`) so current form dominates. `lam_home = att_H * def_A / mu * hfa`,
with the home-field boost `hfa ≈ 1.13` fit from league matches and dropped to 1.0 on
neutral World Cup venues. Shrinkage strength k is tuned over {1,2,4,8,16} by holdout
Brier (k = 1 wins). With no scraper clones present calibrate falls back to the 8
argentina match JSONs.

**90-minute market clock**: the model prices the 1X2 (90 min) market. Matches without
extra time — every league match and every WC group game — fold stoppage-time events into
minute 90 (a 90+4' goal settles the market); in WC knockouts minutes above 90 are extra
time and never enter (`model.effective_min(minute, has_extra_time)`). A knockout that is
level at 90' keeps replaying through extra time to 120': the market stays settled on the
90' score (no more MarketUpdates), while the timeline keeps one row per minute pricing
who wins in extra time on the raw scoreline — so timelines have 91 rows for a 90-minute
match and 121 for one that went the distance.

Back-test (mean Brier per checkpoint vs the 90-minute outcome; temporal holdout: train
on 2022-23..2024-25 leagues + WC2018 + WC2022, evaluate on the 864 held-out 2025-26
league matches + WC2026 — from `assets/data/winprob/model_params.json`):

| Minute | Model (w=0.35) | Baseline (w=0) | Constant base-rate |
| --- | --- | --- | --- |
| 0 | 0.6187 | 0.6092 | 0.6460 |
| 15 | 0.6029 | 0.5841 | 0.6460 |
| 30 | 0.5822 | 0.5589 | 0.6460 |
| 45 | 0.5243 | 0.5135 | 0.6460 |
| 60 | 0.4538 | 0.4460 | 0.6460 |
| 75 | 0.3641 | 0.3610 | 0.6460 |
| 90 | 0.0000 | 0.0000 | 0.6460 |

Both model variants clearly beat the constant always-quote-the-base-rate baseline. The
honest surprise: at this scale the w=0 (score + clock + pre-match rates, no momentum)
variant edges out the momentum blend at most checkpoints — 15-minute xG is noisy, and
w = 0.35 overweights it. The production params keep w = 0.35 for the live-momentum demo,
but the holdout table reports both so the number is not oversold.

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
| Tests | `python3 -m pytest live-pipeline/tests -q` |

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
`assets/data/winprob/model_params.json`), then `build_timelines.py` (rewrites
`assets/data/winprob/<match_id>.json` + `index.json` for the dashboard).

## Files

| File | Purpose |
| --- | --- |
| `run_demo.py` | CLI: replay one match as a live feed and price it (`--list`, `--match`, `--speed`, `--broker`, `--late-join`) |
| `requirements.txt` | Documents that the core has no deps; `pika` optional for rabbit mode |
| `tradepipe/messages.py` | TRADE360-style envelope + builders for MsgTypes 1/2/3/31/35 |
| `tradepipe/broker.py` | `Broker` API, synchronous `InMemoryBroker`, `RabbitBroker` (topic exchange `trade`, RPC) |
| `tradepipe/producer.py` | `MatchProducer`: deterministic minute 0..end replay (90', or 120' after extra time), snapshot authority |
| `tradepipe/snapshot.py` | Snapshot payload contract shared by producer (build) and consumer (parse) |
| `tradepipe/state.py` | `MatchState`: rebuilds score/xG/incidents from the feed, MsgSeq gap detection |
| `tradepipe/consumer.py` | `TradeConsumer`: pricing, MarketUpdate publishing, snapshot recovery, timeline recording |
| `tradepipe/model.py` | `InPlayModel`: `lam_remaining`, Poisson grid, fair odds, book prices |
| `tradepipe/corpus.py` | Loads + normalizes the scraped corpora (EPL, La Liga, WC 2018/2022/2026) |
| `tradepipe/calibrate.py` | Fits per-competition mu, namespaced att/def rates, hfa; tunes k by holdout Brier; writes `model_params.json` + dashboard `winprob_params.js` files |
| `tradepipe/build_timelines.py` | Replays every match through the pipeline, writes `assets/data/winprob/*` |
| `tests/test_model.py` | Model unit tests |
| `tests/test_corpus.py` | Corpus loader tests (synthetic matches_detail fixtures) |
| `tests/test_pipeline.py` | End-to-end pipeline tests (replay, recovery, settlement) + v2 params shape |

## Why this project

- **Deterministic replay of a real feed shape.** Recorded matches become a reproducible
  message stream - fixed timestamps, monotonic MsgSeq - so every pipeline behaviour
  (ordering, gaps, settlement) can be tested exactly, the way feed replays are used to
  debug production trading systems.
- **Sequence-gap detection and snapshot recovery.** The consumer tracks MsgSeq, detects
  gaps, and rebuilds state from a request/reply snapshot channel - the same
  push-feed-plus-Snapshot-API pattern real odds feeds use to keep consumers consistent.
- **Market pricing, not just data plumbing.** The consumer turns raw livescores into an
  actual 1X2 market - probabilities, fair odds, margined book prices - with a calibrated
  model and an honest back-test, including the 90-minute market clock conventions real
  settlement depends on.
- **Explicit message contracts over a real broker.** Typed envelopes, routing keys, a
  topic exchange and an RPC queue, behind a transport abstraction that runs identically
  in-memory (tests) and on RabbitMQ (deployment-shaped).

> Built a real-time sports data pipeline mirroring TRADE360 architecture - RabbitMQ
> producer/consumer with snapshot recovery, TRADE-style message contracts, and an
> in-play Poisson win-probability model calibrated on World Cup xG data, powering
> live dashboards.
