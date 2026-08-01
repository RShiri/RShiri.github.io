"""Integration tests against a real RabbitMQ broker.

Skipped unless TRADEPIPE_RABBIT_URL is set (and pika is installed), so the
default suite stays dependency-free; CI sets it against a rabbitmq:3
service container. What these check is exactly what the in-memory broker
CANNOT: that the routing patterns, the RPC round trip and the durability
settings behave the same way once a real AMQP server is in the middle.

    docker run -d -p 5672:5672 rabbitmq:3
    TRADEPIPE_RABBIT_URL=amqp://guest:guest@localhost:5672/%2F \
        python3 -m pytest live-pipeline/tests/test_rabbit.py -q
"""
import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))              # live-pipeline/ on sys.path

from tradepipe.broker import RabbitBroker          # noqa: E402
from tradepipe.consumer import TradeConsumer       # noqa: E402
from tradepipe.messages import MsgType, keep_alive  # noqa: E402
from tradepipe.producer import MatchProducer       # noqa: E402

URL = os.environ.get("TRADEPIPE_RABBIT_URL")
pytest.importorskip("pika", reason="RabbitBroker needs pika")
pytestmark = pytest.mark.skipif(
    not URL, reason="set TRADEPIPE_RABBIT_URL to run the RabbitMQ integration tests")

REPO = HERE.parent.parent
DATA = REPO / "assets" / "data" / "argentina"
MATCH = DATA / "2026_06_17_Argentina_vs_Algeria.json"


@pytest.fixture
def broker():
    b = RabbitBroker(URL)
    yield b
    b.close()


def drain(b, seconds=2.0):
    """Pump the connection's I/O loop so consumer callbacks actually fire."""
    b._conn.process_data_events(time_limit=seconds)


def test_topic_wildcard_matches_amqp_not_a_prefix(broker):
    """The whole reason pattern_matches was rewritten: "feed.*" must match
    one word, exactly as the real exchange does. If the in-memory broker
    and RabbitMQ ever disagree, this is the test that says so."""
    seen = []
    tag = "t" + uuid.uuid4().hex[:8]
    broker.subscribe("feed.%s.*" % tag, lambda rk, m: seen.append(rk))
    time.sleep(0.3)                               # let the bind take effect
    for key in ("feed.%s.one" % tag, "feed.%s.one.deep" % tag, "feed.%s" % tag):
        broker.publish(key, keep_alive("x", 1, 0))
    drain(broker)
    assert seen == ["feed.%s.one" % tag]


def test_rpc_round_trip(broker):
    queue = "snapshot.test." + uuid.uuid4().hex[:8]
    broker.rpc_serve(queue, lambda payload: {"pong": payload["ping"]})

    caller = RabbitBroker(URL)
    try:
        server = threading.Thread(target=broker._conn.process_data_events,
                                  kwargs={"time_limit": 5}, daemon=True)
        server.start()
        assert caller.rpc_call(queue, {"ping": 42}, timeout=5.0) == {"pong": 42}
    finally:
        caller.close()


def test_messages_are_published_persistent(broker):
    """Durable mode must actually mark messages persistent — otherwise a
    broker restart silently loses the feed."""
    assert broker.durable is True
    props = broker._props(keep_alive("x", 1, 0))
    assert props.delivery_mode == 2
    assert RabbitBroker(URL, durable=False)._props().delivery_mode == 1


def test_full_replay_over_rabbit_prices_and_settles():
    """Producer and consumer on separate connections (pika channels are not
    thread-safe), the consumer draining in its own thread — the same shape
    run_demo uses."""
    pub, sub = RabbitBroker(URL), RabbitBroker(URL)
    try:
        producer = MatchProducer(pub, MATCH, quiet=True)
        consumer = TradeConsumer(sub, producer.fixture_id, quiet=True)
        threading.Thread(target=sub.start, daemon=True).start()
        time.sleep(0.5)                           # let the bind settle

        for _ in producer.replay():
            pub._conn.process_data_events(time_limit=0.001)
        deadline = time.time() + 15
        while time.time() < deadline:
            if consumer.settlement_result is not None:
                break
            time.sleep(0.2)

        assert consumer.settlement_result == "1"
        assert consumer.state.score() == (3, 0)
        assert consumer.state.status == "Finished"
        # every minute priced, and no duplicate rows from redelivery
        minutes = [row["min"] for row in consumer.timeline]
        assert minutes == sorted(set(minutes))
        assert minutes[-1] == producer.end_min
    finally:
        sub.close()
        pub.close()


def test_late_join_recovers_over_rabbit():
    """The snapshot RPC has to work across a real connection, mid-replay,
    while the producer is still publishing."""
    pub, sub = RabbitBroker(URL), RabbitBroker(URL)
    try:
        producer = MatchProducer(pub, MATCH, quiet=True)
        consumer = None
        for t in producer.replay():
            # Serving the snapshot queue needs the producer's I/O loop to
            # run between publishes, which is what _sleep does here.
            producer._sleep(0.002)
            if consumer is None and t == 59:
                consumer = TradeConsumer(sub, producer.fixture_id, quiet=True)
                threading.Thread(target=sub.start, daemon=True).start()
                time.sleep(0.4)

        deadline = time.time() + 15
        while time.time() < deadline and consumer.settlement_result is None:
            time.sleep(0.2)

        assert consumer.recoveries >= 1           # it had to ask for a snapshot
        assert consumer.state.score() == (3, 0)
        assert consumer.settlement_result == "1"
    finally:
        sub.close()
        pub.close()
