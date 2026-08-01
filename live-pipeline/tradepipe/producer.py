"""Feed producer: replays one recorded match as a live TRADE360-style feed.

MatchProducer loads a match JSON (assets/data/argentina/<id>.json) and
replays it on the RAW match clock, minutes 0..end_min, on routing key
"feed.<fixture_id>". end_min is the real final-whistle minute: the file's
maxMin when present (96' for a group game with long stoppage, 123' for
extra time), else 120/90 from the extra-time classification
(corpus.knockout_played_extra_time). A knockout decided by a
stoppage-time winner did NOT play extra time — its replay simply ends
when the match did, in the 90+X' range:

    minute 0    FixtureMetadataUpdate (Status InProgress), then LivescoreUpdate
    each minute LivescoreUpdate (raw scoreboard, cumulative xG, that raw
                minute's shots/goals as Incidents)
    every 10'   KeepAlive
    settle_min  Settlement of the 1X2 (90 min) market — minute 90 when
                extra time follows, else the final whistle (stoppage
                goals count toward the 90-minute market)
    end_min     final LivescoreUpdate, FixtureMetadataUpdate (Finished)

The scoreboard and incidents always carry raw minutes; the 90-minute
market folding (model.effective_min) is used only to settle the market.

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

from .corpus import is_groupish, knockout_played_extra_time
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
        # The argentina files are all World Cup matches with clean stage
        # labels ("Group Stage", "Round of 32", "Final", ...): group-ish
        # stage => never extra time; a knockout played extra time only when
        # corpus.knockout_played_extra_time says so (these files carry no
        # maxMin/pens/shootout fields, so the event-based steps decide: an
        # event past 95' or a level folded 90' score => ET; a regulation
        # win via a stoppage-time goal => no ET, the 90+X' events fold into
        # minute 90 like group-stage stoppage). model.effective_min stays
        # pure; this adapter owns the classification.
        is_knockout = not is_groupish(self.match.get("stage"))
        self.has_extra_time = (is_knockout
                               and knockout_played_extra_time(self.match))
        # The replay runs on the RAW match clock to the real final whistle:
        # maxMin when the file carries it (96' for a group game with long
        # stoppage, 123' for extra time), else 120/90 from the ET flag.
        max_min = self.match.get("maxMin")
        if max_min:
            self.end_min = max(90, min(131, int(max_min)))
        else:
            self.end_min = 120 if self.has_extra_time else 90
        # The 1X2 (90 min) market settles at the final whistle of regulation:
        # minute 90 on this feed's clock when extra time follows, otherwise
        # the end of the replay (stoppage goals count, so the folded score
        # equals the raw final score there).
        self.settle_min = 90 if self.has_extra_time else self.end_min
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
        """Generator over minutes 0..end_min; publishes each minute's
        messages, then yields the minute. The caller controls pacing."""
        for t in range(0, self.end_min + 1):
            if t == 0:
                self._publish_metadata("InProgress", t)
                if not self.quiet:
                    home, away = self.match["home"]["name"], self.match["away"]["name"]
                    print("[producer] %s: %s vs %s, kickoff %s 18:00 UTC"
                          % (self.fixture_id, home, away, self.match["date"]))
            self._publish_livescore(t)
            if t > 0 and t < self.end_min and t % 10 == 0:
                self._publish(keep_alive(self.fixture_id,
                                         self._next_seq(), self._ts(t)))
            if t == self.settle_min:
                self._publish_settlement(t)
            if t == self.end_min:
                self._publish_metadata("Finished", t)
            if t == self.end_min and not self.quiet:
                h, a = self.score_raw_at(self.end_min)
                if self.has_extra_time:
                    print("[producer] full time %d-%d after extra time, fixture "
                          "Finished, 1X2 settled at 90' (%d messages)"
                          % (h, a, self.messages_published))
                else:
                    print("[producer] full time %d-%d at %d', fixture Finished, "
                          "1X2 settled (%d messages)"
                          % (h, a, self.end_min, self.messages_published))
            yield t

    def run(self, instant=False):
        """Replay the whole match. Sleeps 60/speed real seconds per simulated
        minute; instant=True publishes everything back-to-back (tests,
        build_timelines)."""
        delay = 0.0 if instant else 60.0 / self.speed
        for t in self.replay():
            if delay > 0.0 and t < self.end_min:
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
        h, a = self.score_raw_at(t)
        if t <= 45:
            period = "1st Half"
        elif t <= 90 or not self.has_extra_time:
            period = "2nd Half"              # incl. second-half stoppage
        else:
            period = "Extra Time"
        scoreboard = {
            "CurrentPeriod": period,
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
        markets = [{"Name": "1X2 (90 min)", "Status": "Closed",
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
            "MatchLength": self.end_min,     # replay of a recorded match:
                                             # the real final-whistle minute
            "Participants": [
                {"Name": M["home"]["name"], "Position": "1",
                 "Color": M["home"].get("color", "")},
                {"Name": M["away"]["name"], "Position": "2",
                 "Color": M["away"].get("color", "")},
            ],
        }

    def score_at(self, t):
        """(home, away) goals up to and including minute t on the 90-minute
        market clock: stoppage goals fold into minute 90, extra-time goals
        never enter (see model.effective_min). Used only to settle the
        1X2 (90 min) market at t == settle_min."""
        h = a = 0
        for g in self.match["goals"]:
            m = self._eff_min(g["min"])
            if m is not None and m <= t:
                if g["team"] == "home":
                    h += 1
                else:
                    a += 1
        return h, a

    def score_raw_at(self, t):
        """(home, away) RAW goal count up to and including raw minute t —
        the extra-time scoreboard past 90'. No 90-market folding."""
        h = a = 0
        for g in self.match["goals"]:
            if g["min"] <= t:
                if g["team"] == "home":
                    h += 1
                else:
                    a += 1
        return h, a

    def _eff_min(self, event_min):
        return effective_min(event_min, self.has_extra_time)

    def _xg_at(self, side, t):
        """Cumulative RAW xG through minute t - the replay runs on the real
        match clock, so nothing folds for display."""
        return sum(s["xg"] for s in self.match["shots"]
                   if s["team"] == side and s["min"] <= t)

    def _incidents_at(self, t):
        """This raw minute's incidents as wire dicts - a 90+4' shot appears
        at minute 94 on the feed.

        Shots (goals are shots with goal=true) plus any red card the match
        file records. Most scraped matches carry no `cards` array at all -
        the corpora record that a player was sent off but not when (see
        corpus.red_cards) - so this is usually shots only; the branch
        exists because a real feed does supply dismissals, and everything
        downstream (MatchState.reds, the model's red-card multipliers, the
        consumer's market suspension) is already wired for them."""
        out = []
        for s in self.match["shots"]:
            if s["min"] == t:
                out.append({
                    "Min": s["min"],
                    "Team": s["team"],
                    "Type": "Goal" if s.get("goal") else "Shot",
                    "Player": s.get("player", ""),
                    "Xg": s.get("xg", 0.0),
                    "OnTarget": bool(s.get("onTarget")),
                })
        for c in self.match.get("cards") or []:
            if c.get("min") == t and (c.get("type") or "").lower() == "red":
                out.append({
                    "Min": c["min"],
                    "Team": c["team"],
                    "Type": "RedCard",
                    "Player": c.get("player", ""),
                    "Xg": 0.0,
                })
        return out
