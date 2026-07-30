"""End-to-end pipeline tests: producer -> in-memory broker -> consumer.

Run from the repo root:
    python3 -m pytest live-pipeline/tests/test_pipeline.py -q
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))              # live-pipeline/ on sys.path

from tradepipe import MsgType, get_broker         # noqa: E402
from tradepipe.producer import MatchProducer      # noqa: E402
from tradepipe.consumer import TradeConsumer      # noqa: E402

REPO = HERE.parent.parent
DATA = REPO / "assets" / "data" / "argentina"
MATCH = DATA / "2026_06_17_Argentina_vs_Algeria.json"            # group stage
KO_MATCH = DATA / "2026_07_12_Winner_EF_7_vs_Winner_EF_8.json"   # quarterfinal, real ET
SF_MATCH = DATA / "2026_07_15_Winner_QF_3_vs_Winner_QF_4.json"   # semifinal: 90+1' winner, NO ET
PARAMS = REPO / "assets" / "data" / "winprob" / "model_params.json"


def test_model_params_v2_shape():
    """The checked-in params file is v2: per-competition mu, namespaced
    team keys, hfa, and the holdout Brier block the dashboard reads."""
    with open(PARAMS, encoding="utf-8") as f:
        params = json.load(f)
    assert params["version"] == 2
    assert isinstance(params["mu"], dict) and "WC" in params["mu"]
    for mu in params["mu"].values():
        assert 0.5 < mu < 3.0
    assert params["hfa"] >= 1.0              # home teams out-create away teams
    assert params["k"] >= 1 and 0.0 <= params["w"] <= 1.0
    for key, t in params["teams"].items():
        comp, _, name = key.partition("/")
        assert comp in params["mu"] and name
        assert t["att"] > 0 and t["def"] > 0 and t["matches"] >= 1
    brier = params["brier"]
    assert brier["checkpoints"][0] == 0 and brier["checkpoints"][-1] == 90
    assert len(brier["model"]) == len(brier["checkpoints"])
    assert len(brier["baseline_w0"]) == len(brier["checkpoints"])
    # "Argentina" must resolve through the WC namespace for the consumer
    assert "WC/Argentina" in params["teams"]


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

    assert producer.end_min == 90                     # group game: no extra time
    assert len(consumer.timeline) == producer.end_min + 1
    assert [row["min"] for row in consumer.timeline] == list(range(0, producer.end_min + 1))
    for row in consumer.timeline:
        assert abs(row["pH"] + row["pD"] + row["pA"] - 1.0) < 2e-4  # rounded to 4dp
    assert consumer.settlement_result == "1"


def test_knockout_replays_through_extra_time():
    producer, consumer = run_pipeline(KO_MATCH)
    with open(KO_MATCH, encoding="utf-8") as f:
        match = json.load(f)

    # level at 90' in a knockout -> the replay runs through extra time
    assert producer.end_min == 120
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

    # no MarketUpdates past 90' — the 90' market is settled
    assert consumer.markets_published == 91

    # at 120' there is no time left: the probs are the one-hot of the result
    assert (last["pH"], last["pD"], last["pA"]) == (1.0, 0.0, 0.0)


def test_stoppage_winner_is_not_extra_time():
    """The semifinal's only post-90 event is the 91' winner: that's a 90+1'
    stoppage goal, not extra time. The replay ends at 90', the goal folds
    into minute 90, and it settles the 1X2 market."""
    producer, consumer = run_pipeline(SF_MATCH)
    with open(SF_MATCH, encoding="utf-8") as f:
        match = json.load(f)

    assert producer.has_extra_time is False
    assert producer.end_min == 90
    assert len(consumer.timeline) == 91

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
    assert [row["min"] for row in late_rows] == list(range(60, 91))
    assert len(late_rows) == len(full_rows) == 31
    for a, b in zip(late_rows, full_rows):
        assert rows_equal(a, b), (a, b)

    # final states agree in every observable
    fs, ls = full.final_state, late.final_state
    assert (fs.score(), fs.minute, fs.status) == (ls.score(), ls.minute, ls.status)
    assert abs(fs.xg_h - ls.xg_h) < 1e-9 and abs(fs.xg_a - ls.xg_a) < 1e-9
    assert len(fs.incidents) == len(ls.incidents)
    assert fs.last_seq == ls.last_seq
    assert full.settlement_result == late.settlement_result == "1"


def test_msgseq_monotonic_and_markets_routing():
    received = []
    producer, consumer = run_pipeline(MATCH, spy=lambda rk, m: received.append((rk, m)))
    fid = producer.fixture_id

    feed_seqs = [m.msg_seq for rk, m in received if rk == "feed.%s" % fid]
    assert feed_seqs == list(range(1, len(feed_seqs) + 1))     # contiguous from 1
    assert feed_seqs[-1] == producer.messages_published

    market_msgs = [m for rk, m in received if rk == "markets.%s" % fid]
    assert len(market_msgs) == 91
    assert all(m.msg_type == MsgType.MARKET_UPDATE for m in market_msgs)
    market_seqs = [m.msg_seq for m in market_msgs]
    assert market_seqs == list(range(1, 92))                   # monotonic per publisher
    # no MarketUpdates ever leak onto the feed routing key
    assert all(m.msg_type != MsgType.MARKET_UPDATE
               for rk, m in received if rk.startswith("feed."))
