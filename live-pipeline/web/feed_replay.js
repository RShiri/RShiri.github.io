/* Browser-side TRADE360 consumer.
 *
 * A faithful JS port of tradepipe/state.py + the dispatch half of
 * tradepipe/consumer.py, so the live-pipeline page can replay the REAL
 * message envelopes (assets/data/pipeline/<id>.json, written by
 * dump_feed.py from the actual MatchProducer) rather than a pre-computed
 * timeline. Pricing is delegated to winprob_model.js, the same model the
 * Python pipeline uses.
 *
 * What this exists to show, which a pre-baked timeline cannot:
 *   - the message contract itself, envelope by envelope, as it arrives
 *   - MsgSeq gap detection, and snapshot recovery from the producer
 *   - the market suspending on a goal and reopening the next minute
 *
 * The producer is the snapshot authority because it holds every message it
 * has published. The page holds that same array, so `snapshotAt(i)` rebuilds
 * a snapshot exactly as the producer's RPC handler would.
 */
(function (global) {
  "use strict";

  var MsgType = {
    FIXTURE_METADATA_UPDATE: 1, LIVESCORE_UPDATE: 2,
    MARKET_UPDATE: 3, KEEP_ALIVE: 31, SETTLEMENT: 35
  };
  var TYPE_NAME = {
    1: "FixtureMetadataUpdate", 2: "LivescoreUpdate",
    3: "MarketUpdate", 31: "KeepAlive", 35: "Settlement"
  };

  /* ------------------------------------------------------- MatchState */
  function MatchState(fixtureId, fixture) {
    this.fixtureId = fixtureId;
    this.fixture = fixture || {};
    this.minute = 0;
    this.scoreH = 0; this.scoreA = 0;
    this.xgH = 0; this.xgA = 0;
    this.incidents = [];
    this.xgByMin = { home: {}, away: {} };
    this.reds = { home: 0, away: 0 };
    this.lastSeq = 0;
  }
  MatchState.prototype.participant = function (position) {
    var ps = this.fixture.Participants || [];
    for (var i = 0; i < ps.length; i++) if (ps[i].Position === position) return ps[i].Name;
    return null;
  };
  MatchState.prototype.homeName = function () { return this.participant("1"); };
  MatchState.prototype.awayName = function () { return this.participant("2"); };
  MatchState.prototype.status = function () { return this.fixture.Status || "NotStarted"; };

  /* A message is a gap if it is not the next one we expect. */
  MatchState.prototype.seqGap = function (msg) {
    return this.lastSeq > 0 && msg.Header.MsgSeq !== this.lastSeq + 1;
  };

  MatchState.prototype.apply = function (msg) {
    var events = (msg.Body && msg.Body.Events) || [];
    for (var i = 0; i < events.length; i++) {
      var ev = events[i];
      if (ev.Fixture) this.fixture = ev.Fixture;
      if (ev.Livescore) {
        this.applyLivescore(ev.Livescore.Scoreboard, ev.Livescore.Statistics,
                            ev.Livescore.Incidents);
      }
    }
    this.lastSeq = msg.Header.MsgSeq;
  };

  MatchState.prototype.applyLivescore = function (scoreboard, statistics, incidents) {
    if (scoreboard) {
      if (scoreboard.Time != null) this.minute = scoreboard.Time;
      if (scoreboard.HomeScore != null) this.scoreH = scoreboard.HomeScore;
      if (scoreboard.AwayScore != null) this.scoreA = scoreboard.AwayScore;
    }
    (statistics || []).forEach(function (s) {
      if (s.Type === "xG") {
        if (s.Home != null) this.xgH = s.Home;
        if (s.Away != null) this.xgA = s.Away;
      }
    }, this);
    (incidents || []).forEach(function (inc) {
      this.incidents.push(inc);
      if (inc.Type === "RedCard") {
        if (this.reds[inc.Team] != null) this.reds[inc.Team] += 1;
        return;                                   // a dismissal carries no xG
      }
      var ledger = this.xgByMin[inc.Team];
      if (!ledger) return;
      var m = inc.Min || 0;
      ledger[m] = (ledger[m] || 0) + (inc.Xg || 0);
    }, this);
  };

  MatchState.prototype.xgRecent = function (team, window) {
    var t = this.minute, ledger = this.xgByMin[team], total = 0;
    for (var k in ledger) {
      var m = +k;
      if (m > t - window && m <= t) total += ledger[k];
    }
    return total;
  };

  MatchState.fromSnapshot = function (payload) {
    var live = payload.Livescore || {};
    var st = new MatchState(payload.FixtureId, payload.Fixture || {});
    st.applyLivescore(live.Scoreboard || {}, live.Statistics || [],
                      live.Incidents || []);
    st.lastSeq = payload.LastMsgSeq || 0;
    return st;
  };

  /* ------------------------------------------------------- the consumer */
  function Consumer(feed, params, opts) {
    opts = opts || {};
    this.feed = feed;
    this.params = params;
    this.onEvent = opts.onEvent || function () {};
    this.reset();
  }

  Consumer.prototype.reset = function () {
    this.state = null;
    this.model = null;
    this.cursor = 0;                 // next index in feed.messages to deliver
    this.timeline = [];
    this.received = 0;
    this.dropped = 0;                // messages the transport "lost"
    this.duplicates = 0;
    this.recoveries = 0;
    this.marketsPublished = 0;
    this.settlement = null;
    this.marketStatus = "Open";
    this.seenGuids = {};
    this.last = null;                // last priced snapshot, for the UI
  };

  /* The producer's snapshot authority, reproduced: fold every message it
     has published so far into a fresh state and report its LastMsgSeq. */
  Consumer.prototype.snapshotAt = function (deliveredUpTo) {
    var msgs = this.feed.messages, st = new MatchState(this.feed.fixtureId, {});
    var lastSeq = 0;
    for (var i = 0; i < deliveredUpTo; i++) {
      st.apply(msgs[i]);
      lastSeq = msgs[i].Header.MsgSeq;
    }
    return {
      FixtureId: this.feed.fixtureId,
      Fixture: st.fixture,
      Livescore: {
        Scoreboard: { CurrentPeriod: "", Time: st.minute,
                      HomeScore: st.scoreH, AwayScore: st.scoreA },
        Statistics: [{ Type: "xG", Home: st.xgH, Away: st.xgA }],
        Incidents: st.incidents
      },
      LastMsgSeq: lastSeq
    };
  };

  Consumer.prototype.buildModel = function () {
    if (!global.WinProb || !this.state) return;
    var params = this.params;
    var prefix = (params && params.competition ? params.competition : "WC");
    // The page loads the full model_params.json, whose team keys are
    // namespaced ("WC/Argentina"); flatten the slice this fixture needs.
    var teams = {}, keys = Object.keys(params.teams || {});
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i], cut = k.indexOf("/");
      if (cut > 0 && k.slice(0, cut) === prefix) teams[k.slice(cut + 1)] = params.teams[k];
      else if (cut < 0) teams[k] = params.teams[k];
    }
    var flat = {
      mu: (params.mu && params.mu[prefix]) || params.mu,
      hfa: 1, neutral: true,                     // every World Cup venue is neutral
      w: params.w, window: params.window, profile: params.profile,
      rho: params.rho, bLead: params.b_lead, bTrail: params.b_trail,
      red: params.red, maxGoals: 10, lamFloor: 0.05, teams: teams
    };
    this.model = global.WinProb.forMatch(flat, this.state.homeName(), this.state.awayName());
  };

  /* Deliver the next message. `drop` marks it as lost in transit: the
     consumer never sees it, which is what creates the MsgSeq gap. */
  Consumer.prototype.step = function (drop) {
    var msgs = this.feed.messages;
    if (this.cursor >= msgs.length) return null;
    var msg = msgs[this.cursor++];
    if (drop) {
      this.dropped++;
      return { kind: "dropped", msg: msg, type: msg.Header.Type,
               name: TYPE_NAME[msg.Header.Type], seq: msg.Header.MsgSeq };
    }
    return this.handle(msg);
  };

  Consumer.prototype.handle = function (msg) {
    var h = msg.Header, type = h.Type;
    var out = { kind: "applied", msg: msg, type: type, name: TYPE_NAME[type],
                seq: h.MsgSeq, recovered: false, duplicate: false };

    if (this.seenGuids[h.MsgGuid]) {             // redelivery, not a gap
      this.duplicates++;
      out.kind = "duplicate"; out.duplicate = true;
      return out;
    }
    this.seenGuids[h.MsgGuid] = 1;
    this.received++;

    if (type === MsgType.FIXTURE_METADATA_UPDATE) {
      if (!this.state) {
        this.state = new MatchState(msg.Body.Events[0].FixtureId,
                                    msg.Body.Events[0].Fixture);
        this.state.lastSeq = h.MsgSeq;
        this.buildModel();
      } else {
        this.state.apply(msg);
      }
    } else if (type === MsgType.LIVESCORE_UPDATE) {
      if (this.state && h.MsgSeq <= this.state.lastSeq) {
        this.duplicates++; out.kind = "duplicate"; out.duplicate = true;
        return out;
      }
      if (!this.state || this.state.seqGap(msg)) {
        var expected = this.state ? this.state.lastSeq + 1 : 1;
        this.state = MatchState.fromSnapshot(this.snapshotAt(this.cursor - 1));
        if (!this.model) this.buildModel();
        this.recoveries++;
        out.recovered = true;
        out.expected = expected;
        out.recoveredTo = this.state.lastSeq;
      }
      if (h.MsgSeq <= this.state.lastSeq) {      // covered by the snapshot
        out.kind = "covered";
        return out;
      }
      this.state.apply(msg);
      out.priced = this.price(msg);
    } else if (type === MsgType.KEEP_ALIVE) {
      if (this.state) {
        if (h.MsgSeq <= this.state.lastSeq) {
          this.duplicates++; out.kind = "duplicate";
        } else if (this.state.seqGap(msg)) {
          var exp = this.state.lastSeq + 1;
          this.state = MatchState.fromSnapshot(this.snapshotAt(this.cursor - 1));
          this.recoveries++;
          out.recovered = true; out.expected = exp;
          out.recoveredTo = this.state.lastSeq;
        } else {
          this.state.apply(msg);
        }
      }
    } else if (type === MsgType.SETTLEMENT) {
      if (this.state) this.state.apply(msg);
      (msg.Body.Events || []).forEach(function (ev) {
        (ev.Markets || []).forEach(function (mk) {
          (mk.Bets || []).forEach(function (bet) {
            if (bet.Settlement === 1) this.settlement = bet.Name;
          }, this);
        }, this);
      }, this);
      this.marketStatus = "Closed";
      if (this.timeline.length) this.timeline[this.timeline.length - 1].status = "Closed";
      out.settled = this.settlement;
    }
    return out;
  };

  Consumer.prototype.price = function (msg) {
    var st = this.state;
    if (!this.model) return null;
    var horizon = null;
    if (st.minute > 90) {
      var length = st.fixture.MatchLength || 120;
      horizon = Math.max(0, length - st.minute) / 90;
    }
    var win = this.params.window || 15;
    var pr = this.model.probsAt(st.minute, {
      scoreH: st.scoreH, scoreA: st.scoreA,
      xgH: st.xgRecent("home", win), xgA: st.xgRecent("away", win),
      redH: st.reds.home, redA: st.reds.away,
      horizon: horizon
    });

    var events = [];
    (msg.Body.Events || []).forEach(function (ev) {
      ((ev.Livescore && ev.Livescore.Incidents) || []).forEach(function (inc) {
        events.push({
          min: inc.Min, team: inc.Team,
          type: inc.Type === "Goal" ? "goal" : inc.Type === "RedCard" ? "red" : "shot",
          player: inc.Player || "", xg: inc.Xg || 0
        });
      });
    });
    var halting = events.filter(function (e) { return e.type === "goal" || e.type === "red"; });
    if (this.settlement === null) {
      this.marketStatus = halting.length ? "Suspended" : "Open";
      this.marketsPublished++;
    } else {
      this.marketStatus = "Closed";
    }

    var row = {
      min: st.minute, pH: pr[0], pD: pr[1], pA: pr[2],
      fairH: fair(pr[0]), fairD: fair(pr[1]), fairA: fair(pr[2]),
      scoreH: st.scoreH, scoreA: st.scoreA, xgH: st.xgH, xgA: st.xgA,
      status: this.marketStatus, events: events, halting: halting
    };
    this.timeline.push(row);
    this.last = row;
    return row;
  };

  function fair(p) { return p < 0.001 ? 999 : 1 / p; }

  global.FeedReplay = {
    Consumer: Consumer,
    MatchState: MatchState,
    MsgType: MsgType,
    TYPE_NAME: TYPE_NAME,
    fairOdds: fair
  };
})(window);
