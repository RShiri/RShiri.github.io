"""TRADE360-style message contracts.

Every message on the wire is a JSON envelope:

    {"Header": {"Type": <int>, "MsgGuid": "<uuid4>",
                "MsgSeq": <int, per-fixture monotonically increasing>,
                "ServerTimestamp": <epoch ms>,
                "CreationDate": "<ISO 8601 UTC>"},
     "Body": {"Events": [ {...}, ... ]}}

Each event dict inside Body.Events carries "FixtureId". Body payload
conventions per message type:

FixtureMetadataUpdate (Type 1) event:
    {"FixtureId", "Fixture": {"Sport": "Football", "Venue", "Stage",
     "StartDate", "Status": "NotStarted"|"InProgress"|"Finished",
     "Participants": [{"Name", "Position": "1"|"2", "Color"}]}}

LivescoreUpdate (Type 2) event:
    {"FixtureId", "Livescore": {
     "Scoreboard": {"CurrentPeriod", "Time" (minute int),
                    "HomeScore", "AwayScore"},
     "Statistics": [{"Type": "xG", "Home": float, "Away": float}],
     "Incidents": [per-minute shot/goal dicts]}}

MarketUpdate (Type 3) / Settlement (Type 35) event:
    {"FixtureId", "Markets": [{"Name": "1X2 (90 min)",
     "Bets": [{"Name": "1"|"X"|"2", "Probability": float,
               "Price": float, "BookPrice": float}]}]}

KeepAlive (Type 31) event: {"FixtureId"} only.

Timestamps are supplied by callers so replays are deterministic; the
current wall clock is only a fallback when ts_ms is omitted.
"""
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


class MsgType:
    FIXTURE_METADATA_UPDATE = 1
    LIVESCORE_UPDATE = 2
    MARKET_UPDATE = 3
    KEEP_ALIVE = 31
    SETTLEMENT = 35


def _iso_utc(ts_ms):
    """Epoch ms -> ISO 8601 UTC string (e.g. 2026-06-14T18:00:00.000Z)."""
    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (ts_ms % 1000)


@dataclass
class Message:
    """One TRADE360-style envelope: header fields + Body dict."""
    msg_type: int
    msg_seq: int
    server_timestamp: int                       # epoch ms
    body: dict = field(default_factory=lambda: {"Events": []})
    msg_guid: str = field(default_factory=lambda: str(uuid.uuid4()))
    creation_date: str = ""

    def __post_init__(self):
        if not self.creation_date:
            self.creation_date = _iso_utc(self.server_timestamp)

    def to_dict(self):
        return {
            "Header": {
                "Type": self.msg_type,
                "MsgGuid": self.msg_guid,
                "MsgSeq": self.msg_seq,
                "ServerTimestamp": self.server_timestamp,
                "CreationDate": self.creation_date,
            },
            "Body": self.body,
        }

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_dict(cls, d):
        h = d["Header"]
        return cls(msg_type=h["Type"], msg_seq=h["MsgSeq"],
                   server_timestamp=h["ServerTimestamp"], body=d["Body"],
                   msg_guid=h["MsgGuid"], creation_date=h["CreationDate"])

    @classmethod
    def from_json(cls, s):
        return cls.from_dict(json.loads(s))

    @property
    def events(self):
        return self.body.get("Events") or []

    @property
    def fixture_id(self):
        """FixtureId of the first event, or None on an empty body."""
        ev = self.events
        return ev[0].get("FixtureId") if ev else None


def _make(msg_type, events, msg_seq, ts_ms):
    if ts_ms is None:
        ts_ms = int(time.time() * 1000)         # fallback only; pass ts_ms for replay
    return Message(msg_type=msg_type, msg_seq=msg_seq,
                   server_timestamp=int(ts_ms), body={"Events": events})


def fixture_metadata_update(fixture_id, fixture_dict, msg_seq, ts_ms=None):
    """Type 1: fixture metadata (venue, stage, status, participants)."""
    return _make(MsgType.FIXTURE_METADATA_UPDATE,
                 [{"FixtureId": fixture_id, "Fixture": fixture_dict}], msg_seq, ts_ms)


def livescore_update(fixture_id, scoreboard, statistics, incidents, msg_seq, ts_ms=None):
    """Type 2: scoreboard + statistics (xG) + per-minute incidents."""
    return _make(MsgType.LIVESCORE_UPDATE,
                 [{"FixtureId": fixture_id, "Livescore": {
                     "Scoreboard": scoreboard,
                     "Statistics": statistics,
                     "Incidents": incidents}}], msg_seq, ts_ms)


def market_update(fixture_id, markets, msg_seq, ts_ms=None):
    """Type 3: in-play odds. markets is a list of market dicts (see module doc)."""
    return _make(MsgType.MARKET_UPDATE,
                 [{"FixtureId": fixture_id, "Markets": markets}], msg_seq, ts_ms)


def keep_alive(fixture_id, msg_seq, ts_ms=None):
    """Type 31: heartbeat for one fixture."""
    return _make(MsgType.KEEP_ALIVE, [{"FixtureId": fixture_id}], msg_seq, ts_ms)


def settlement(fixture_id, markets, msg_seq, ts_ms=None):
    """Type 35: final settlement of the fixture's markets."""
    return _make(MsgType.SETTLEMENT,
                 [{"FixtureId": fixture_id, "Markets": markets}], msg_seq, ts_ms)
