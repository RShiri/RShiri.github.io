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
| replay 0'..90' |      |                 |      |  MatchState      |
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
| 2 | LivescoreUpdate | Every simulated minute 0..90 | `Scoreboard` (period, minute, score), `Statistics` (cumulative xG), `Incidents` (that minute's shots/goals with xG) |
| 3 | MarketUpdate | Consumer output, per priced minute | `Markets`: 1X2 (90 min) with `Probability`, fair `Price`, `BookPrice` (5% overround) |
| 31 | KeepAlive | Every 10 simulated minutes | `FixtureId` only (heartbeat) |
| 35 | Settlement | Full time | 1X2 bets with `Settlement` 1/0 |

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
shrinkage (k = 1 pseudo-match at the tournament baseline `mu = 1.4325` xG per
team-match), `lam(A vs B) = att_A * def_B / mu`, no home advantage (neutral WC venues).

**90-minute market clock**: the model prices the 1X2 (90 min) market, so group-stage
stoppage-time events fold into minute 90 (a 90+4' goal settles the market) while knockout
minutes above 90 are extra time and never enter the replay (`model.effective_min`).

Back-test (mean Brier per checkpoint vs the 90-minute outcome, from
`assets/data/winprob/model_params.json`):

| Minute | Model (w=0.35) | Baseline (w=0) |
| --- | --- | --- |
| 0 | 0.7076 | 0.8387 |
| 15 | 0.7043 | 0.7867 |
| 30 | 0.7894 | 0.7581 |
| 45 | 0.6453 | 0.6804 |
| 60 | 0.4990 | 0.5208 |
| 75 | 0.4240 | 0.4352 |
| 90 | 0.0000 | 0.0000 |

The momentum model beats the pre-match-only baseline at 6 of 7 checkpoints - but n = 8
matches, so treat this as a smoke test, not a benchmark.

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
| `tradepipe/producer.py` | `MatchProducer`: deterministic minute 0..90 replay, snapshot authority |
| `tradepipe/snapshot.py` | Snapshot payload contract shared by producer (build) and consumer (parse) |
| `tradepipe/state.py` | `MatchState`: rebuilds score/xG/incidents from the feed, MsgSeq gap detection |
| `tradepipe/consumer.py` | `TradeConsumer`: pricing, MarketUpdate publishing, snapshot recovery, timeline recording |
| `tradepipe/model.py` | `InPlayModel`: `lam_remaining`, Poisson grid, fair odds, book prices |
| `tradepipe/calibrate.py` | Fits team att/def rates (shrinkage k=1) + Brier back-test, writes `model_params.json` |
| `tradepipe/build_timelines.py` | Replays every match through the pipeline, writes `assets/data/winprob/*` |
| `tests/test_model.py` | Model unit tests |
| `tests/test_pipeline.py` | End-to-end pipeline tests (replay, recovery, settlement) |

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
