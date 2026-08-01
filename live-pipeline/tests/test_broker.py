"""Tests for the transport layer (tradepipe/broker.py).

The routing tests matter more than they look: the in-memory broker is what
every other test runs on, so if its pattern matching disagrees with AMQP's,
the whole suite can pass while the RabbitMQ deployment misroutes. These
pin the semantics to the real ones.

Run from the repo root:
    python3 -m pytest live-pipeline/tests/test_broker.py -q
"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))              # live-pipeline/ on sys.path

from tradepipe.broker import (InMemoryBroker, get_broker,  # noqa: E402
                              pattern_matches)
from tradepipe.messages import keep_alive          # noqa: E402


@pytest.mark.parametrize("pattern,key,expected", [
    # exact keys
    ("feed.abc", "feed.abc", True),
    ("feed.abc", "feed.abd", False),
    # "*" is EXACTLY one word — not a prefix. This is the bug the old
    # implementation had: it treated "feed.*" as "starts with feed.".
    ("feed.*", "feed.abc", True),
    ("feed.*", "feed.abc.markets", False),
    ("feed.*", "feed", False),
    ("*.abc", "feed.abc", True),
    ("*.abc", "feed.x.abc", False),
    # "#" is zero or more words
    ("#", "anything.at.all", True),
    ("#", "single", True),
    ("feed.#", "feed.abc", True),
    ("feed.#", "feed.abc.markets", True),
    ("feed.#", "feed", True),
    ("feed.#", "markets.abc", False),
    # mixed
    ("*.*.markets", "a.b.markets", True),
    ("*.*.markets", "a.markets", False),
])
def test_pattern_matches_amqp_semantics(pattern, key, expected):
    assert pattern_matches(pattern, key) is expected


def test_wildcard_delivers_every_fixture_but_not_deeper_keys():
    broker = InMemoryBroker()
    seen = []
    broker.subscribe("feed.*", lambda rk, m: seen.append(rk))
    for key in ("feed.match1", "feed.match2", "feed.match2.deep", "markets.match1"):
        broker.publish(key, keep_alive("x", 1, 0))
    assert seen == ["feed.match1", "feed.match2"]


def test_publish_dispatches_in_subscription_order():
    broker = InMemoryBroker()
    order = []
    broker.subscribe("#", lambda rk, m: order.append("first"))
    broker.subscribe("feed.a", lambda rk, m: order.append("second"))
    broker.publish("feed.a", keep_alive("a", 1, 0))
    assert order == ["first", "second"]


def test_rpc_round_trip_and_missing_handler():
    broker = InMemoryBroker()
    broker.rpc_serve("snapshot.a", lambda payload: {"echo": payload["v"]})
    assert broker.rpc_call("snapshot.a", {"v": 7}) == {"echo": 7}
    with pytest.raises(RuntimeError):
        broker.rpc_call("snapshot.missing", {})


def test_get_broker_factory():
    assert isinstance(get_broker("memory"), InMemoryBroker)
    with pytest.raises(ValueError):
        get_broker("carrier-pigeon")
