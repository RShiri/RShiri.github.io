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
MATCH = DATA / "2026_06_17_Argentina_vs_Algeria.json"


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

    assert len(consumer.timeline) == 91
    assert [row["min"] for row in consumer.timeline] == list(range(0, 91))
    for row in consumer.timeline:
        assert abs(row["pH"] + row["pD"] + row["pA"] - 1.0) < 2e-4  # rounded to 4dp
    assert consumer.settlement_result == "1"


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
