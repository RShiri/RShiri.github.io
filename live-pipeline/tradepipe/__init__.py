"""tradepipe: a mini TRADE360-style sports-data pipeline. Football fixtures
are replayed as a live feed — fixture metadata, per-minute livescores and
in-play 1X2 odds — as JSON envelopes over a pluggable broker (in-memory for
tests and deterministic replay, RabbitMQ topic exchange for the real demo),
with a snapshot request/reply channel on the side."""
from .messages import (
    MsgType,
    Message,
    fixture_metadata_update,
    livescore_update,
    market_update,
    keep_alive,
    settlement,
)
from .broker import Broker, InMemoryBroker, RabbitBroker, get_broker

FIXTURE_METADATA_UPDATE = MsgType.FIXTURE_METADATA_UPDATE
LIVESCORE_UPDATE = MsgType.LIVESCORE_UPDATE
MARKET_UPDATE = MsgType.MARKET_UPDATE
KEEP_ALIVE = MsgType.KEEP_ALIVE
SETTLEMENT = MsgType.SETTLEMENT
