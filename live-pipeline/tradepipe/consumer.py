"""Trading consumer: turns the livescore feed into in-play 1X2 prices.

TradeConsumer subscribes to "feed.<fixture_id>" and, per LivescoreUpdate,
runs the InPlayModel (pre-match rates from model_params.json, the fitted
remaining-scoring profile, score-state and red-card adjustments) and
publishes a MarketUpdate on "markets.<fixture_id>". It also records one
timeline row per minute:

    {"min": t,
     "pH": ..., "pD": ..., "pA": ...,          # win/draw/win probabilities
     "fairH": ..., "fairD": ..., "fairA": ...,  # no-margin decimal odds
     "xgH": ..., "xgA": ...,                    # cumulative xG
     "scoreH": ..., "scoreA": ...,
     "status": "Open"|"Suspended"|"Closed",     # 1X2 market state
     "events": [{"min", "team", "type": "goal"|"shot"|"red", "player", "xg"}]}

MARKET STATE. A real book does not quote through a goal: the market
suspends the moment one goes in, reprices, and reopens. This consumer does
the same — a minute whose incidents contain a goal or a red card publishes
a SUSPENDED MarketUpdate carrying no prices, and the next minute reopens
with the new number. Settlement closes it for good. Suspended minutes still
record a timeline row (the probabilities are what the model thinks; they
are simply not tradeable at that instant).

Past 90' the timeline keeps one row per minute on the raw match clock,
pricing the final result with the same formula over the minutes left to
the real final whistle (the fixture's MatchLength): second-half stoppage
first — where the 1X2 market is still open and MarketUpdates keep
flowing until Settlement lands — then extra time, where the market is
settled and rows are recorded only. At the whistle the probabilities
collapse to the result (level at 120' -> pD = 1: the tie goes to
penalties).

RECOVERY. If a LivescoreUpdate arrives with no local state (late join) or
with a MsgSeq gap (missed messages), the consumer calls the RPC queue
"snapshot.<fixture_id>", rebuilds MatchState from the reply, drops anything
the snapshot already covers, and carries on seamlessly. Redelivered
messages — which a durable broker with manual acks WILL produce — are
dropped by MsgGuid and by sequence before any of that, so a duplicate is
never mistaken for a gap.
"""
import json
from pathlib import Path

from .messages import MsgType, market_update
from .calibrate import prematch_lams
from .model import InPlayModel
from .state import MatchState

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_PARAMS = REPO / "assets" / "data" / "winprob" / "model_params.json"

MARKET_NAME = "1X2 (90 min)"
OPEN, SUSPENDED, CLOSED = "Open", "Suspended", "Closed"
SEEN_GUID_LIMIT = 4096                  # bounded dedup memory per fixture


class TradeConsumer:

    def __init__(self, broker, fixture_id, params_path=None, quiet=False,
                 competition="WC", subscribe=True):
        self.broker = broker
        self.fixture_id = fixture_id
        self.quiet = quiet
        self.competition = competition
        with open(params_path or DEFAULT_PARAMS, encoding="utf-8") as f:
            params = json.load(f)
        # v2/v3 params: mu is per-competition and team keys are namespaced
        # ("WC/Argentina"). The argentina fixtures are all World Cup games,
        # so this consumer prices with the "WC" slice; unknown countries
        # fall back to mu inside prematch_lams.
        self.params = params
        self.mu = params["mu"][competition]

        self.state = None                   # MatchState once metadata/snapshot seen
        self.model = None                   # InPlayModel once team names known
        self.timeline = []                  # one row per priced minute
        self.messages_received = 0
        self.markets_published = 0          # doubles as markets MsgSeq counter
        self.recoveries = 0
        self.duplicates_dropped = 0
        self.settlement_result = None       # "1"/"X"/"2" once settled
        self.market_status = OPEN
        self._seen_guids = set()
        self._guid_order = []

        # A MultiFixtureConsumer owns the subscription and routes to us.
        if subscribe:
            self.broker.subscribe("feed.%s" % fixture_id, self._on_message)

    @property
    def final_state(self):
        return self.state

    # -------------------------------------------------------------- dispatch

    def _duplicate(self, message):
        """True if this exact message has already been handled.

        A durable broker with manual acknowledgement redelivers anything
        that was not acked, so duplicates are normal operation, not an
        error. MsgGuid identifies the message; the set is bounded because a
        feed runs indefinitely and memory does not."""
        guid = message.msg_guid
        if guid in self._seen_guids:
            return True
        self._seen_guids.add(guid)
        self._guid_order.append(guid)
        if len(self._guid_order) > SEEN_GUID_LIMIT:
            self._seen_guids.discard(self._guid_order.pop(0))
        return False

    def _on_message(self, routing_key, message):
        if self._duplicate(message):
            self.duplicates_dropped += 1
            return
        self.messages_received += 1
        mtype = message.msg_type

        if mtype == MsgType.FIXTURE_METADATA_UPDATE:
            if self.state is None:
                self.state = MatchState.from_metadata(message.events[0],
                                                      msg_seq=message.msg_seq)
                self._build_model()
            else:
                self.state.apply(message)   # e.g. Status -> Finished

        elif mtype == MsgType.LIVESCORE_UPDATE:
            # Order matters: a message we have already applied is a
            # REDELIVERY, not a gap. Checking sequence first stops a
            # duplicate from triggering a pointless snapshot RPC.
            if self.state is not None and message.msg_seq <= self.state.last_seq:
                self.duplicates_dropped += 1
                return
            if self.state is None or self.state.seq_gap(message):
                self._recover(message)
            if message.msg_seq <= self.state.last_seq:
                return                      # already covered by the snapshot
            self.state.apply(message)
            self._price_minute(message)

        elif mtype == MsgType.KEEP_ALIVE:
            # A heartbeat that skips a sequence proves messages were lost
            # even though no livescore has arrived to reveal it — recover
            # now rather than waiting for the next minute.
            if self.state is None:
                return
            if message.msg_seq <= self.state.last_seq:
                self.duplicates_dropped += 1
            elif self.state.seq_gap(message):
                self._recover(message)
            else:
                self.state.apply(message)

        elif mtype == MsgType.SETTLEMENT:
            self._on_settlement(message)

    # -------------------------------------------------------------- recovery

    def _recover(self, message):
        expected = self.state.last_seq + 1 if self.state is not None else 1
        payload = self.broker.rpc_call("snapshot.%s" % self.fixture_id,
                                       {"FixtureId": self.fixture_id})
        self.state = MatchState.from_snapshot(payload)
        if self.model is None:
            self._build_model()
        self.recoveries += 1
        if not self.quiet:
            print("[consumer] seq gap detected (got seq %d, expected %d), "
                  "snapshot recovered: %d-%d @ %d' (LastMsgSeq %d)"
                  % (message.msg_seq, expected, self.state.score_h,
                     self.state.score_a, self.state.minute,
                     self.state.last_seq))

    def _build_model(self):
        # World Cup venues are neutral, so no home-advantage boost (hfa=1).
        prefix = self.competition + "/"
        lam_h, lam_a = prematch_lams(self.params["teams"], self.mu,
                                     prefix + (self.state.home_name or ""),
                                     prefix + (self.state.away_name or ""),
                                     hfa=1.0)
        self.model = InPlayModel.from_params(lam_h, lam_a, self.params)

    # --------------------------------------------------------------- pricing

    def _price_minute(self, message):
        st = self.state
        horizon = None
        if st.minute > 90:
            # Past the 90-minute market clock the fitted profile no longer
            # applies: price the minutes left to the real final whistle.
            length = st.fixture.get("MatchLength") or 120
            horizon = max(0, length - st.minute) / 90.0
        p = self.model.probs(st.minute, st.score_h, st.score_a,
                             st.xg_recent("home", self.model.window),
                             st.xg_recent("away", self.model.window),
                             red_h=st.reds_h, red_a=st.reds_a, horizon=horizon)

        events = self._events_of(message)
        # A goal or a dismissal moves the price discontinuously; a real book
        # pulls the market rather than quoting through it.
        halting = [e for e in events if e["type"] in ("goal", "red")]

        if self.settlement_result is None:
            status = SUSPENDED if halting else OPEN
            self.market_status = status
            self._publish_market(message, p, status)
        else:
            self.market_status = CLOSED

        row = {
            "min": st.minute,
            "pH": round(p["pH"], 4), "pD": round(p["pD"], 4), "pA": round(p["pA"], 4),
            "fairH": round(p["fairH"], 3), "fairD": round(p["fairD"], 3),
            "fairA": round(p["fairA"], 3),
            "xgH": round(st.xg_h, 3), "xgA": round(st.xg_a, 3),
            "scoreH": st.score_h, "scoreA": st.score_a,
            "status": self.market_status,
            "events": events,
        }
        self.timeline.append(row)

        if not self.quiet:
            marks = "".join(
                "  GOAL %s" % e["player"] if e["type"] == "goal"
                else "  RED %s" % e["player"] for e in halting)
            flag = " [SUSPENDED]" if self.market_status == SUSPENDED else ""
            print("%3d' %d-%d | xG %.2f-%.2f | P %.1f/%.1f/%.1f | "
                  "fair %.2f/%.2f/%.2f%s%s"
                  % (st.minute, st.score_h, st.score_a, st.xg_h, st.xg_a,
                     100 * p["pH"], 100 * p["pD"], 100 * p["pA"],
                     p["fairH"], p["fairD"], p["fairA"], marks, flag))

    def _publish_market(self, message, p, status):
        """One MarketUpdate. A suspended market carries its status and no
        prices — quoting a number you would not accept a bet at is worse
        than quoting nothing."""
        self.markets_published += 1
        if status == SUSPENDED:
            bets = [{"Name": name} for name in ("1", "X", "2")]
        else:
            bets = [
                {"Name": "1", "Probability": round(p["pH"], 6),
                 "Price": round(p["fairH"], 3), "BookPrice": round(p["bookH"], 3)},
                {"Name": "X", "Probability": round(p["pD"], 6),
                 "Price": round(p["fairD"], 3), "BookPrice": round(p["bookD"], 3)},
                {"Name": "2", "Probability": round(p["pA"], 6),
                 "Price": round(p["fairA"], 3), "BookPrice": round(p["bookA"], 3)},
            ]
        markets = [{"Name": MARKET_NAME, "Status": status, "Bets": bets}]
        self.broker.publish("markets.%s" % self.fixture_id,
                            market_update(self.fixture_id, markets,
                                          self.markets_published,
                                          message.server_timestamp))

    @staticmethod
    def _events_of(message):
        events = []
        for ev in message.events:
            live = ev.get("Livescore") or {}
            for inc in live.get("Incidents") or []:
                kind = inc.get("Type")
                events.append({
                    "min": inc.get("Min"),
                    "team": inc.get("Team"),
                    "type": ("goal" if kind == "Goal"
                             else "red" if kind == "RedCard" else "shot"),
                    "player": inc.get("Player", ""),
                    "xg": inc.get("Xg", 0.0),
                })
        return events

    # ------------------------------------------------------------ settlement

    def _on_settlement(self, message):
        if self.state is not None:
            self.state.apply(message)       # records the MsgSeq
        names = {"1": "home win", "X": "draw", "2": "away win"}
        for ev in message.events:
            for market in ev.get("Markets") or []:
                for bet in market.get("Bets") or []:
                    if bet.get("Settlement") == 1:
                        self.settlement_result = bet["Name"]
        self.market_status = CLOSED
        # The minute that was just priced is the one the whistle closed, so
        # correct its row rather than leaving the timeline's last tradeable
        # state reading Open on a settled market.
        if self.timeline:
            self.timeline[-1]["status"] = CLOSED
        if not self.quiet and self.settlement_result:
            print("[consumer] settlement: %s -> '%s' (%s) pays, others void to 0"
                  % (MARKET_NAME, self.settlement_result,
                     names.get(self.settlement_result, "?")))


class MultiFixtureConsumer:
    """One subscription, every fixture on the feed.

    A trading consumer in production does not open a connection per match;
    it binds one pattern and fans out internally. This binds "feed.*" —
    which, with proper AMQP semantics, matches exactly one word after
    "feed." and so picks up every fixture id without also swallowing
    "feed.x.y" — and lazily spins up a TradeConsumer the first time each
    fixture id appears. Each per-fixture consumer keeps its own MatchState,
    model, sequence tracking and recovery, so a gap on one match never
    disturbs another.

    Late joiners work exactly as they do for a single fixture: the first
    message seen for an unknown fixture has no local state, so that
    fixture's consumer recovers from its own snapshot RPC."""

    def __init__(self, broker, params_path=None, quiet=False,
                 competition="WC", pattern="feed.*"):
        self.broker = broker
        self.params_path = params_path
        self.quiet = quiet
        self.competition = competition
        self.consumers = {}                 # fixture_id -> TradeConsumer
        self.messages_received = 0
        self.broker.subscribe(pattern, self._on_message)

    def _on_message(self, routing_key, message):
        self.messages_received += 1
        fixture_id = message.fixture_id
        if fixture_id is None:
            _, _, fixture_id = routing_key.partition(".")
        if not fixture_id:
            return
        consumer = self.consumers.get(fixture_id)
        if consumer is None:
            consumer = TradeConsumer(self.broker, fixture_id,
                                     params_path=self.params_path,
                                     quiet=self.quiet,
                                     competition=self.competition,
                                     subscribe=False)
            self.consumers[fixture_id] = consumer
        consumer._on_message(routing_key, message)

    @property
    def fixtures(self):
        return sorted(self.consumers)

    def timeline(self, fixture_id):
        consumer = self.consumers.get(fixture_id)
        return consumer.timeline if consumer else []
