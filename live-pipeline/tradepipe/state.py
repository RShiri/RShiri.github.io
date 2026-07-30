"""Consumer-side view of one fixture, rebuilt from the message feed.

MatchState is fed FixtureMetadataUpdate / LivescoreUpdate / KeepAlive
messages via apply() and keeps: current minute, score, cumulative xG,
the full incident list, and a per-minute xG ledger so the in-play model
can ask "how much xG did each side create in the last 15 minutes?".

It also tracks MsgSeq: seq_gap(message) says whether a message is NOT
the next expected one (call it BEFORE apply). A gapped consumer rebuilds
itself from a snapshot payload via MatchState.from_snapshot().
"""
from .snapshot import parse_snapshot


class MatchState:

    def __init__(self, fixture_id, fixture=None):
        self.fixture_id = fixture_id
        self.fixture = fixture or {}         # last known Fixture metadata dict
        self.minute = 0
        self.score_h = 0
        self.score_a = 0
        self.xg_h = 0.0                      # cumulative xG (from Statistics)
        self.xg_a = 0.0
        self.incidents = []                  # every incident seen, in order
        self.xg_by_min = {"home": {}, "away": {}}   # minute -> xG created then
        self.last_seq = 0                    # MsgSeq of the last applied message

    # ---------------------------------------------------------- constructors

    @classmethod
    def from_metadata(cls, event, msg_seq=0):
        """Build from a FixtureMetadataUpdate event dict
        ({"FixtureId": ..., "Fixture": {...}})."""
        state = cls(event["FixtureId"], event.get("Fixture"))
        state.last_seq = msg_seq
        return state

    @classmethod
    def from_snapshot(cls, payload):
        """Build mid-match state from a snapshot payload (see snapshot.py)."""
        snap = parse_snapshot(payload)
        state = cls(snap["fixture_id"], snap["fixture"])
        state._apply_livescore(snap["scoreboard"], snap["statistics"],
                               snap["incidents"])
        state.last_seq = snap["last_seq"]
        return state

    # ------------------------------------------------------------ properties

    @property
    def status(self):
        return self.fixture.get("Status", "NotStarted")

    @property
    def home_name(self):
        return self._participant("1")

    @property
    def away_name(self):
        return self._participant("2")

    def _participant(self, position):
        for p in self.fixture.get("Participants") or []:
            if p.get("Position") == position:
                return p.get("Name")
        return None

    # -------------------------------------------------------------- sequence

    def seq_gap(self, message):
        """True if message is not the next expected MsgSeq. Check BEFORE
        apply(); a fresh-from-metadata state expects last_seq + 1 next."""
        return self.last_seq > 0 and message.msg_seq != self.last_seq + 1

    # ----------------------------------------------------------------- apply

    def apply(self, message):
        """Fold one feed message into the state and record its MsgSeq."""
        for event in message.events:
            if "Fixture" in event:
                self.fixture = event["Fixture"]
            if "Livescore" in event:
                live = event["Livescore"]
                self._apply_livescore(live.get("Scoreboard"),
                                      live.get("Statistics"),
                                      live.get("Incidents"))
        self.last_seq = message.msg_seq

    def _apply_livescore(self, scoreboard, statistics, incidents):
        if scoreboard:
            self.minute = scoreboard.get("Time", self.minute)
            self.score_h = scoreboard.get("HomeScore", self.score_h)
            self.score_a = scoreboard.get("AwayScore", self.score_a)
        for stat in statistics or []:
            if stat.get("Type") == "xG":
                self.xg_h = stat.get("Home", self.xg_h)
                self.xg_a = stat.get("Away", self.xg_a)
        for inc in incidents or []:
            self.incidents.append(inc)
            ledger = self.xg_by_min.get(inc.get("Team"))
            if ledger is not None:
                minute = inc.get("Min", 0)
                ledger[minute] = ledger.get(minute, 0.0) + inc.get("Xg", 0.0)

    # ------------------------------------------------------------- questions

    def xg_recent15(self, team):
        """xG the side ("home"/"away") created in minutes (t-15, t]."""
        t = self.minute
        ledger = self.xg_by_min[team]
        return sum(xg for minute, xg in ledger.items() if t - 15 < minute <= t)

    def score(self):
        return self.score_h, self.score_a
