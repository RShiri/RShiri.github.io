"""End-to-end pipeline tests: producer -> in-memory broker -> consumer.

Run from the repo root:
    python3 -m pytest live-pipeline/tests/test_pipeline.py -q
"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))              # live-pipeline/ on sys.path

from tradepipe import MsgType, get_broker         # noqa: E402
from tradepipe.messages import keep_alive, livescore_update   # noqa: E402
from tradepipe.producer import MatchProducer      # noqa: E402
from tradepipe.consumer import (MultiFixtureConsumer,         # noqa: E402
                                TradeConsumer)

REPO = HERE.parent.parent
DATA = REPO / "assets" / "data" / "argentina"
MATCH = DATA / "2026_06_17_Argentina_vs_Algeria.json"            # group stage
KO_MATCH = DATA / "2026_07_12_Winner_EF_7_vs_Winner_EF_8.json"   # quarterfinal, real ET
SF_MATCH = DATA / "2026_07_15_Winner_QF_3_vs_Winner_QF_4.json"   # semifinal: 90+1' winner, NO ET
PARAMS = REPO / "assets" / "data" / "winprob" / "model_params.json"


def test_model_params_v3_shape():
    """The checked-in params file is v3: per-competition mu, namespaced team
    keys, hfa, the fitted model shape, and the holdout block the explainer
    reads."""
    with open(PARAMS, encoding="utf-8") as f:
        params = json.load(f)
    assert params["version"] == 3
    assert isinstance(params["mu"], dict) and "WC" in params["mu"]
    for mu in params["mu"].values():
        assert 0.5 < mu < 3.0
    assert params["hfa"] >= 1.0              # home teams out-create away teams
    assert params["k"] >= 1 and 0.0 <= params["w"] <= 1.0
    assert 0.0 < params["decay"] <= 1.0
    assert params["window"] >= 1
    assert -1.0 <= params["rho"] <= 1.0
    red = params["red"]
    assert red["self"] > 0 and red["opp"] > 0
    for key, t in params["teams"].items():
        comp, _, name = key.partition("/")
        assert comp in params["mu"] and name
        assert t["att"] > 0 and t["def"] > 0 and t["matches"] >= 1
    # "Argentina" must resolve through the WC namespace for the consumer
    assert "WC/Argentina" in params["teams"]


def test_model_params_profile_is_a_valid_survival_curve():
    """profile[t] is the share of a match's xG still to come after minute t:
    one row per minute, never rising, nothing left at the whistle."""
    with open(PARAMS, encoding="utf-8") as f:
        profile = json.load(f)["profile"]
    if profile is None:
        return                               # fallback fit: linear clock
    assert len(profile) == 91
    assert 0.9 <= profile[0] <= 1.0
    assert profile[-1] == 0.0
    for earlier, later in zip(profile, profile[1:]):
        assert later <= earlier + 1e-9


def test_model_params_holdout_block_is_complete():
    with open(PARAMS, encoding="utf-8") as f:
        brier = json.load(f)["brier"]
    cps = brier["checkpoints"]
    assert cps[0] == 0 and cps[-1] == 90
    for key in ("model", "baseline_v2", "baseline_w0", "constant", "logloss"):
        assert len(brier[key]) == len(cps), key
    # the holdout is scored once, by the finished model, and it must beat
    # both the previous version and the always-quote-the-base-rate baseline
    means = brier["mean_brier"]
    assert means["model"] < means["baseline_v2"] < means["constant"]
    assert means["model"] < means["baseline_w0"]
    # calibration is reported, and the shipped model is better calibrated
    assert brier["ece"]["model"] < brier["ece"]["baseline_v2"]
    assert len(brier["reliability"]["model"]) == 10


def run_pipeline(match_path, late_join=None, spy=None):
    """Instant in-memory replay. late_join=N attaches the consumer only
    after minute N-1 has been published. spy(routing_key, message) may be
    subscribed to everything. Returns (producer, consumer)."""
    broker = get_broker("memory")
    if spy is not None:
        broker.subscribe("#", spy)
    producer = MatchProducer(broker, match_path, quiet=True)
    consumer = None
    if late_join is None:
        consumer = TradeConsumer(broker, producer.fixture_id, quiet=True)
        producer.run(instant=True)
    else:
        for t in producer.replay():
            if consumer is None and t == late_join - 1:
                consumer = TradeConsumer(broker, producer.fixture_id, quiet=True)
    return producer, consumer


def rows_equal(a, b, tol=1e-9):
    """Deep equality of timeline rows with float tolerance."""
    if type(a) is dict and type(b) is dict:
        return a.keys() == b.keys() and all(rows_equal(a[k], b[k], tol) for k in a)
    if type(a) is list and type(b) is list:
        return len(a) == len(b) and all(rows_equal(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b) <= tol
    return a == b


def test_full_replay_argentina_algeria():
    producer, consumer = run_pipeline(MATCH)
    with open(MATCH, encoding="utf-8") as f:
        match = json.load(f)

    assert consumer.final_state is not None
    assert consumer.final_state.score() == (3, 0)
    assert consumer.final_state.score() == (match["home"]["score"],
                                            match["away"]["score"])
    assert consumer.final_state.status == "Finished"

    # group game: raw clock to the real final whistle (maxMin), no ET
    assert producer.has_extra_time is False
    assert producer.end_min == match["maxMin"] == 96
    assert producer.settle_min == producer.end_min    # market settles at the whistle
    assert len(consumer.timeline) == producer.end_min + 1
    assert [row["min"] for row in consumer.timeline] == list(range(0, producer.end_min + 1))
    for row in consumer.timeline:
        assert abs(row["pH"] + row["pD"] + row["pA"] - 1.0) < 2e-4  # rounded to 4dp
    assert consumer.settlement_result == "1"


def test_knockout_replays_through_extra_time():
    producer, consumer = run_pipeline(KO_MATCH)
    with open(KO_MATCH, encoding="utf-8") as f:
        match = json.load(f)

    # level at 90' in a knockout -> the replay runs through extra time,
    # to the real final whistle on the ET clock
    assert producer.has_extra_time is True
    assert producer.end_min == match["maxMin"] == 123
    assert producer.settle_min == 90
    assert len(consumer.timeline) == producer.end_min + 1
    assert [row["min"] for row in consumer.timeline] == list(range(0, producer.end_min + 1))

    # the final recorded score is the match's real full-time score
    last = consumer.timeline[-1]
    assert (last["scoreH"], last["scoreA"]) == (match["home"]["score"],
                                                match["away"]["score"])
    assert consumer.final_state.status == "Finished"

    # settlement still fires at 90' with the 90' result
    h90, a90 = producer.score_at(90)
    expected = "1" if h90 > a90 else ("X" if h90 == a90 else "2")
    assert consumer.settlement_result == expected == "X"
    row90 = consumer.timeline[90]
    assert (row90["scoreH"], row90["scoreA"]) == (h90, a90)

    # no MarketUpdates past the 90' settlement — extra time is off-market
    assert consumer.markets_published == 91

    # at the whistle there is no time left: probs are the one-hot result
    assert (last["pH"], last["pD"], last["pA"]) == (1.0, 0.0, 0.0)


def test_stoppage_winner_is_not_extra_time():
    """The semifinal ended in second-half stoppage (maxMin 101, winner at
    90+1'): no extra time. The replay runs the raw clock to the whistle,
    shows the goal at its real minute, and the stoppage goal settles the
    1X2 market."""
    producer, consumer = run_pipeline(SF_MATCH)
    with open(SF_MATCH, encoding="utf-8") as f:
        match = json.load(f)

    assert producer.has_extra_time is False
    assert producer.end_min == match["maxMin"] == 101
    assert producer.settle_min == producer.end_min
    assert len(consumer.timeline) == producer.end_min + 1
    # the 91' winner appears at its raw minute on the feed
    assert any(e["min"] == 91 and e["type"] == "goal"
               for row in consumer.timeline for e in row["events"])

    last = consumer.timeline[-1]
    assert (last["scoreH"], last["scoreA"]) == (match["home"]["score"],
                                                match["away"]["score"]) == (2, 1)
    assert consumer.settlement_result == "1"
    assert (last["pH"], last["pD"], last["pA"]) == (1.0, 0.0, 0.0)


def test_late_join_recovers_and_matches_uninterrupted():
    _, full = run_pipeline(MATCH)
    _, late = run_pipeline(MATCH, late_join=60)

    assert late.recoveries == 1
    late_rows = late.timeline
    full_rows = [row for row in full.timeline if row["min"] >= 60]
    end = len(full.timeline) - 1
    assert [row["min"] for row in late_rows] == list(range(60, end + 1))
    assert len(late_rows) == len(full_rows) == end - 59
    for a, b in zip(late_rows, full_rows):
        assert rows_equal(a, b), (a, b)

    # final states agree in every observable
    fs, ls = full.final_state, late.final_state
    assert (fs.score(), fs.minute, fs.status) == (ls.score(), ls.minute, ls.status)
    assert abs(fs.xg_h - ls.xg_h) < 1e-9 and abs(fs.xg_a - ls.xg_a) < 1e-9
    assert len(fs.incidents) == len(ls.incidents)
    assert fs.last_seq == ls.last_seq
    assert full.settlement_result == late.settlement_result == "1"


def market_status_by_minute(received, fixture_id):
    """{MarketUpdate index -> Status} in publish order for one fixture."""
    out = []
    for rk, m in received:
        if rk == "markets.%s" % fixture_id and m.msg_type == MsgType.MARKET_UPDATE:
            for ev in m.events:
                for market in ev.get("Markets") or []:
                    out.append(market.get("Status"))
    return out


# ----------------------------------------------------- market state machine

def test_market_suspends_on_a_goal_and_reopens_after():
    """A book does not quote through a goal. The minute a goal lands the
    1X2 market goes Suspended and carries no prices; the next minute it is
    Open again at the new number."""
    _, consumer = run_pipeline(MATCH)
    rows = consumer.timeline
    goal_minutes = sorted({e["min"] for row in rows for e in row["events"]
                           if e["type"] == "goal"})
    assert goal_minutes, "the fixture under test must contain a goal"

    by_min = {row["min"]: row for row in rows}
    for minute in goal_minutes:
        assert by_min[minute]["status"] == "Suspended", minute
        nxt = by_min.get(minute + 1)
        if nxt is not None and not any(e["type"] in ("goal", "red")
                                       for e in nxt["events"]):
            assert nxt["status"] == "Open", minute

    # quiet minutes are tradeable
    quiet = [r for r in rows if not r["events"] and r["min"] < 90]
    assert quiet and all(r["status"] == "Open" for r in quiet)


def test_suspended_market_update_carries_no_prices():
    received = []
    producer, _ = run_pipeline(MATCH, spy=lambda rk, m: received.append((rk, m)))
    fid = producer.fixture_id
    suspended = []
    for rk, m in received:
        if rk != "markets.%s" % fid:
            continue
        for ev in m.events:
            for market in ev.get("Markets") or []:
                if market.get("Status") == "Suspended":
                    suspended.append(market)
    assert suspended, "a goal in this fixture must suspend the market"
    for market in suspended:
        for bet in market["Bets"]:
            assert bet["Name"] in ("1", "X", "2")
            assert "Price" not in bet and "Probability" not in bet


def test_market_closes_at_settlement():
    _, consumer = run_pipeline(MATCH)
    assert consumer.market_status == "Closed"
    assert consumer.timeline[-1]["status"] == "Closed"


# --------------------------------------------------- duplicates & ordering

def test_duplicate_delivery_is_dropped_without_recovering():
    """A durable broker with manual acks redelivers. A redelivered message
    is not a gap: it must be dropped, and must NOT trigger a snapshot RPC
    or a second timeline row."""
    broker = get_broker("memory")
    producer = MatchProducer(broker, MATCH, quiet=True)
    consumer = TradeConsumer(broker, producer.fixture_id, quiet=True)

    seen = []
    broker.subscribe("feed.%s" % producer.fixture_id,
                     lambda rk, m: seen.append((rk, m)))
    producer.run(instant=True)

    rows_before = len(consumer.timeline)
    recoveries_before = consumer.recoveries
    # replay every message a second time, exactly as a redelivery would
    for rk, m in seen:
        consumer._on_message(rk, m)

    assert consumer.recoveries == recoveries_before   # no snapshot requested
    assert len(consumer.timeline) == rows_before      # no duplicate rows
    assert consumer.duplicates_dropped >= len(seen)


def test_stale_message_after_recovery_is_ignored():
    """After a snapshot the consumer holds a high LastMsgSeq. Late-arriving
    older messages must not rewind the state."""
    _, late = run_pipeline(MATCH, late_join=60)
    assert late.recoveries == 1
    state_before = (late.state.minute, late.state.score(), late.state.last_seq)
    rows_before = len(late.timeline)

    stale = livescore_update(late.fixture_id,
                             {"CurrentPeriod": "1st Half", "Time": 5,
                              "HomeScore": 9, "AwayScore": 9},
                             [{"Type": "xG", "Home": 0.0, "Away": 0.0}], [],
                             msg_seq=3, ts_ms=0)
    late._on_message("feed.%s" % late.fixture_id, stale)

    assert (late.state.minute, late.state.score(), late.state.last_seq) == state_before
    assert len(late.timeline) == rows_before


def test_keepalive_gap_triggers_recovery():
    """A heartbeat that skips a sequence proves messages were lost before
    any livescore arrives to reveal it — recover on the heartbeat."""
    broker = get_broker("memory")
    producer = MatchProducer(broker, MATCH, quiet=True)
    consumer = TradeConsumer(broker, producer.fixture_id, quiet=True)
    gen = producer.replay()
    for _ in range(12):                      # get well into the match
        next(gen)
    assert consumer.recoveries == 0

    gapped = keep_alive(producer.fixture_id,
                        msg_seq=consumer.state.last_seq + 25, ts_ms=0)
    consumer._on_message("feed.%s" % producer.fixture_id, gapped)
    assert consumer.recoveries == 1


# ---------------------------------------------------------------- red cards

def test_red_card_is_carried_through_the_feed_and_suspends_the_market(tmp_path):
    """The corpora record dismissals without minutes, so no scraped fixture
    exercises this path — but a real feed supplies them, so the pipeline is
    tested against a fixture that does."""
    with open(MATCH, encoding="utf-8") as f:
        match = json.load(f)
    match["cards"] = [{"team": "away", "min": 33, "type": "red",
                       "player": "Sent Off"}]
    path = tmp_path / "red_card_fixture.json"
    path.write_text(json.dumps(match), encoding="utf-8")

    broker = get_broker("memory")
    producer = MatchProducer(broker, path, quiet=True)
    consumer = TradeConsumer(broker, producer.fixture_id, quiet=True)
    producer.run(instant=True)

    row = next(r for r in consumer.timeline if r["min"] == 33)
    assert any(e["type"] == "red" and e["team"] == "away" for e in row["events"])
    assert row["status"] == "Suspended"          # a dismissal halts the market
    assert consumer.state.reds_a == 1 and consumer.state.reds_h == 0
    # a dismissal is not a shot: it must not add xG
    assert consumer.state.xg_a == pytest.approx(
        sum(s["xg"] for s in match["shots"] if s["team"] == "away"), abs=1e-6)


# ------------------------------------------------------------ multi-fixture

def test_multi_fixture_consumer_prices_every_match_on_one_subscription():
    """One "feed.*" binding, one consumer per fixture, no cross-talk."""
    broker = get_broker("memory")
    router = MultiFixtureConsumer(broker, quiet=True)
    producers = [MatchProducer(broker, DATA / (mid + ".json"), quiet=True)
                 for mid in (MATCH.stem, SF_MATCH.stem)]
    for producer in producers:
        producer.run(instant=True)

    assert router.fixtures == sorted(p.fixture_id for p in producers)
    for producer in producers:
        consumer = router.consumers[producer.fixture_id]
        assert len(consumer.timeline) == producer.end_min + 1
        assert consumer.settlement_result is not None
        assert consumer.state.fixture_id == producer.fixture_id

    # each fixture priced the same as it would have alone
    _, solo = run_pipeline(MATCH)
    shared = router.consumers[producers[0].fixture_id]
    assert len(shared.timeline) == len(solo.timeline)
    for a, b in zip(shared.timeline, solo.timeline):
        assert rows_equal(a, b), (a, b)


def test_msgseq_monotonic_and_markets_routing():
    received = []
    producer, consumer = run_pipeline(MATCH, spy=lambda rk, m: received.append((rk, m)))
    fid = producer.fixture_id

    feed_seqs = [m.msg_seq for rk, m in received if rk == "feed.%s" % fid]
    assert feed_seqs == list(range(1, len(feed_seqs) + 1))     # contiguous from 1
    assert feed_seqs[-1] == producer.messages_published

    # the 1X2 market stays open through stoppage: one MarketUpdate per
    # minute until Settlement lands at the whistle
    market_msgs = [m for rk, m in received if rk == "markets.%s" % fid]
    assert len(market_msgs) == producer.settle_min + 1
    assert all(m.msg_type == MsgType.MARKET_UPDATE for m in market_msgs)
    market_seqs = [m.msg_seq for m in market_msgs]
    assert market_seqs == list(range(1, len(market_msgs) + 1))  # monotonic per publisher
    # no MarketUpdates ever leak onto the feed routing key
    assert all(m.msg_type != MsgType.MARKET_UPDATE
               for rk, m in received if rk.startswith("feed."))
