"""Trading consumer: turns the livescore feed into in-play 1X2 prices.

TradeConsumer subscribes to "feed.<fixture_id>" and, per LivescoreUpdate,
runs the InPlayModel (pre-match rates from model_params.json blended with
15-minute xG momentum) and publishes a MarketUpdate on
"markets.<fixture_id>". It also records one timeline row per minute:

    {"min": t,
     "pH": ..., "pD": ..., "pA": ...,          # win/draw/win probabilities
     "fairH": ..., "fairD": ..., "fairA": ...,  # no-margin decimal odds
     "xgH": ..., "xgA": ...,                    # cumulative xG
     "scoreH": ..., "scoreA": ...,
     "events": [{"min", "team", "type": "goal"|"shot", "player", "xg"}, ...]}

Recovery: if a LivescoreUpdate arrives with no local state (late join) or
with a MsgSeq gap (missed messages), the consumer calls the RPC queue
"snapshot.<fixture_id>", rebuilds MatchState from the reply, drops anything
the snapshot already covers, and carries on seamlessly.
"""
import json
from pathlib import Path

from .messages import MsgType, market_update
from .calibrate import prematch_lams
from .model import InPlayModel
from .state import MatchState

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_PARAMS = REPO / "assets" / "data" / "winprob" / "model_params.json"


class TradeConsumer:

    def __init__(self, broker, fixture_id, params_path=None, quiet=False):
        self.broker = broker
        self.fixture_id = fixture_id
        self.quiet = quiet
        with open(params_path or DEFAULT_PARAMS, encoding="utf-8") as f:
            params = json.load(f)
        self.mu = params["mu"]
        self.w = params.get("w", 0.35)
        self.teams = params["teams"]        # unknown names fall back to mu

        self.state = None                   # MatchState once metadata/snapshot seen
        self.model = None                   # InPlayModel once team names known
        self.timeline = []                  # one row per priced minute
        self.messages_received = 0
        self.markets_published = 0          # doubles as markets MsgSeq counter
        self.recoveries = 0
        self.settlement_result = None       # "1"/"X"/"2" once settled

        self.broker.subscribe("feed.%s" % fixture_id, self._on_message)

    @property
    def final_state(self):
        return self.state

    # -------------------------------------------------------------- dispatch

    def _on_message(self, routing_key, message):
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
            if self.state is None or self.state.seq_gap(message):
                self._recover(message)
            if message.msg_seq <= self.state.last_seq:
                return                      # already covered by the snapshot
            self.state.apply(message)
            self._price_minute(message)

        elif mtype == MsgType.KEEP_ALIVE:
            if self.state is not None and not self.state.seq_gap(message):
                self.state.apply(message)
            # a gapped keep-alive is ignored; the next livescore recovers

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
        lam_h, lam_a = prematch_lams(self.teams, self.mu,
                                     self.state.home_name,
                                     self.state.away_name)
        self.model = InPlayModel(lam_h, lam_a, w=self.w)

    # --------------------------------------------------------------- pricing

    def _price_minute(self, message):
        st = self.state
        p = self.model.probs(st.minute, st.score_h, st.score_a,
                             st.xg_recent15("home"), st.xg_recent15("away"))

        self.markets_published += 1
        markets = [{"Name": "1X2 (90 min)", "Bets": [
            {"Name": "1", "Probability": round(p["pH"], 6),
             "Price": round(p["fairH"], 3), "BookPrice": round(p["bookH"], 3)},
            {"Name": "X", "Probability": round(p["pD"], 6),
             "Price": round(p["fairD"], 3), "BookPrice": round(p["bookD"], 3)},
            {"Name": "2", "Probability": round(p["pA"], 6),
             "Price": round(p["fairA"], 3), "BookPrice": round(p["bookA"], 3)},
        ]}]
        self.broker.publish("markets.%s" % self.fixture_id,
                            market_update(self.fixture_id, markets,
                                          self.markets_published,
                                          message.server_timestamp))

        events = []
        for ev in message.events:
            live = ev.get("Livescore") or {}
            for inc in live.get("Incidents") or []:
                events.append({
                    "min": inc.get("Min"),
                    "team": inc.get("Team"),
                    "type": "goal" if inc.get("Type") == "Goal" else "shot",
                    "player": inc.get("Player", ""),
                    "xg": inc.get("Xg", 0.0),
                })

        row = {
            "min": st.minute,
            "pH": round(p["pH"], 4), "pD": round(p["pD"], 4), "pA": round(p["pA"], 4),
            "fairH": round(p["fairH"], 3), "fairD": round(p["fairD"], 3),
            "fairA": round(p["fairA"], 3),
            "xgH": round(st.xg_h, 3), "xgA": round(st.xg_a, 3),
            "scoreH": st.score_h, "scoreA": st.score_a,
            "events": events,
        }
        self.timeline.append(row)

        if not self.quiet:
            goals = "".join("  GOAL %s" % e["player"]
                            for e in events if e["type"] == "goal")
            print("%3d' %d-%d | xG %.2f-%.2f | P %.1f/%.1f/%.1f | "
                  "fair %.2f/%.2f/%.2f%s"
                  % (st.minute, st.score_h, st.score_a, st.xg_h, st.xg_a,
                     100 * p["pH"], 100 * p["pD"], 100 * p["pA"],
                     p["fairH"], p["fairD"], p["fairA"], goals))

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
        if not self.quiet and self.settlement_result:
            print("[consumer] settlement: %s -> '%s' (%s) pays, others void to 0"
                  % ("1X2 (90 min)", self.settlement_result,
                     names.get(self.settlement_result, "?")))
