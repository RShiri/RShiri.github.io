"""Feed producer: replays one recorded match as a live TRADE360-style feed.

MatchProducer loads a match JSON (assets/data/argentina/<id>.json) and
replays minutes 0..90 on routing key "feed.<fixture_id>":

    minute 0    FixtureMetadataUpdate (Status InProgress), then LivescoreUpdate
    each minute LivescoreUpdate (scoreboard, cumulative xG, that minute's
                shots/goals as Incidents)
    every 10'   KeepAlive
    minute 90   final LivescoreUpdate, FixtureMetadataUpdate (Finished),
                Settlement of the 1X2 (90 min) market

Timestamps are deterministic (kickoff = match date at 18:00 UTC, +1 simulated
minute = +60000 ms) and MsgSeq is a per-fixture counter starting at 1.

The producer is also the fixture's snapshot authority: it serves RPC queue
"snapshot.<fixture_id>" (registered in __init__, i.e. before replay) with the
current replay state so late joiners can catch up (see snapshot.py).

replay() is a generator yielding after each minute, so a caller (run_demo,
build_timelines) can interleave its own logic — e.g. attach a consumer
mid-match. run() drives replay() with real pacing: 60/speed seconds per
simulated minute (speed=600 -> ~9 s total), or no sleeping with instant=True.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .messages import (fixture_metadata_update, livescore_update, keep_alive,
                       settlement)
from .model import effective_min
from .snapshot import build_snapshot

KICKOFF_HOUR_UTC = 18


class MatchProducer:

    def __init__(self, broker, match_path, speed=60.0, quiet=False):
        self.broker = broker
        self.match_path = Path(match_path)
        self.speed = float(speed)
        self.quiet = quiet
        with open(self.match_path, encoding="utf-8") as f:
            self.match = json.load(f)
        self.fixture_id = self.match_path.stem
        self.kickoff_ms = self._kickoff_ms(self.match["date"])
        self.messages_published = 0          # doubles as the MsgSeq counter

        # Snapshot-authority state: what the feed has published so far.
        self._fixture = None                 # last published Fixture metadata
        self._scoreboard = None
        self._statistics = None
        self._incidents = []                 # cumulative published incidents
        self._last_pub_seq = 0               # MsgSeq of last delivered message

        # Serve snapshots BEFORE any replay starts.
        self.broker.rpc_serve("snapshot.%s" % self.fixture_id,
                              self._snapshot_handler)

    # ------------------------------------------------------------- replaying

    def replay(self):
        """Generator over minutes 0..90; publishes each minute's messages,
        then yields the minute. The caller controls pacing."""
        for t in range(0, 91):
            if t == 0:
                self._publish_metadata("InProgress", t)
                if not self.quiet:
                    home, away = self.match["home"]["name"], self.match["away"]["name"]
                    print("[producer] %s: %s vs %s, kickoff %s 18:00 UTC"
                          % (self.fixture_id, home, away, self.match["date"]))
            self._publish_livescore(t)
            if t > 0 and t < 90 and t % 10 == 0:
                self._publish(keep_alive(self.fixture_id,
                                         self._next_seq(), self._ts(t)))
            if t == 90:
                self._publish_metadata("Finished", t)
                self._publish_settlement(t)
                if not self.quiet:
                    h, a = self.score_at(90)
                    print("[producer] full time %d-%d, fixture Finished, "
                          "1X2 settled (%d messages)" % (h, a, self.messages_published))
            yield t

    def run(self, instant=False):
        """Replay the whole match. Sleeps 60/speed real seconds per simulated
        minute; instant=True publishes everything back-to-back (tests,
        build_timelines)."""
        delay = 0.0 if instant else 60.0 / self.speed
        for t in self.replay():
            if delay > 0.0 and t < 90:
                self._sleep(delay)

    def _sleep(self, seconds):
        """Pace the replay. On a RabbitBroker, drive the connection's I/O loop
        instead of sleeping so snapshot RPC requests are served in between
        publishes; the in-memory broker just sleeps."""
        conn = getattr(self.broker, "_conn", None)
        if conn is not None:
            conn.process_data_events(time_limit=seconds)
        else:
            time.sleep(seconds)

    # ------------------------------------------------------------ publishing

    def _publish(self, message):
        self.broker.publish("feed.%s" % self.fixture_id, message)
        # For the sync in-memory broker this line runs AFTER dispatch, so a
        # snapshot requested while handling message N reports LastMsgSeq N-1
        # and the requester can then apply N itself with no gap.
        self._last_pub_seq = message.msg_seq

    def _publish_metadata(self, status, t):
        fixture = self._fixture_dict(status)
        msg = fixture_metadata_update(self.fixture_id, fixture,
                                      self._next_seq(), self._ts(t))
        self._publish(msg)
        self._fixture = fixture

    def _publish_livescore(self, t):
        h, a = self.score_at(t)
        scoreboard = {
            "CurrentPeriod": "1st Half" if t <= 45 else "2nd Half",
            "Time": t,
            "HomeScore": h,
            "AwayScore": a,
        }
        statistics = [{"Type": "xG",
                       "Home": round(self._xg_at("home", t), 4),
                       "Away": round(self._xg_at("away", t), 4)}]
        incidents = self._incidents_at(t)
        msg = livescore_update(self.fixture_id, scoreboard, statistics,
                               incidents, self._next_seq(), self._ts(t))
        self._publish(msg)
        self._scoreboard = scoreboard
        self._statistics = statistics
        self._incidents.extend(incidents)

    def _publish_settlement(self, t):
        h, a = self.score_at(90)
        winner = "1" if h > a else ("X" if h == a else "2")
        markets = [{"Name": "1X2 (90 min)",
                    "Bets": [{"Name": name, "Settlement": 1 if name == winner else 0}
                             for name in ("1", "X", "2")]}]
        self._publish(settlement(self.fixture_id, markets,
                                 self._next_seq(), self._ts(t)))

    # -------------------------------------------------------------- snapshot

    def _snapshot_handler(self, payload):
        """RPC: current replay state for late joiners / gap recovery."""
        return build_snapshot(self.fixture_id, self._fixture, self._scoreboard,
                              self._statistics, self._incidents,
                              self._last_pub_seq)

    # --------------------------------------------------------------- helpers

    def _next_seq(self):
        self.messages_published += 1
        return self.messages_published

    def _ts(self, minute):
        return self.kickoff_ms + minute * 60000

    @staticmethod
    def _kickoff_ms(date_str):
        """Match "date" (YYYY-MM-DD) -> kickoff epoch ms at 18:00 UTC."""
        y, m, d = (int(x) for x in date_str.split("-"))
        dt = datetime(y, m, d, KICKOFF_HOUR_UTC, 0, 0, tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)

    def _fixture_dict(self, status):
        M = self.match
        return {
            "Sport": "Football",
            "Venue": M.get("venue", ""),
            "Stage": M.get("stage", ""),
            "StartDate": "%sT%02d:00:00.000Z" % (M["date"], KICKOFF_HOUR_UTC),
            "Status": status,
            "Participants": [
                {"Name": M["home"]["name"], "Position": "1",
                 "Color": M["home"].get("color", "")},
                {"Name": M["away"]["name"], "Position": "2",
                 "Color": M["away"].get("color", "")},
            ],
        }

    def score_at(self, t):
        """(home, away) goals up to and including minute t on the 90-minute
        market clock: group-stage stoppage goals fold into minute 90,
        extra-time goals never enter the replay (see model.effective_min)."""
        h = a = 0
        for g in self.match["goals"]:
            m = self._eff_min(g["min"])
            if m is not None and m <= t:
                if g["team"] == "home":
                    h += 1
                else:
                    a += 1
        return h, a

    def _eff_min(self, event_min):
        return effective_min(event_min, self.match.get("stage", ""))

    def _xg_at(self, side, t):
        total = 0.0
        for s in self.match["shots"]:
            m = self._eff_min(s["min"])
            if s["team"] == side and m is not None and m <= t:
                total += s["xg"]
        return total

    def _incidents_at(self, t):
        """This minute's shots (goals are shots with goal=true) as wire dicts."""
        out = []
        for s in self.match["shots"]:
            if self._eff_min(s["min"]) == t:
                out.append({
                    "Min": t,
                    "Team": s["team"],
                    "Type": "Goal" if s.get("goal") else "Shot",
                    "Player": s.get("player", ""),
                    "Xg": s.get("xg", 0.0),
                    "OnTarget": bool(s.get("onTarget")),
                })
        return out
