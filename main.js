/* ===========================================================================
   Ram Shiri - portfolio interactions (dependency-free).
   Nav + scrollspy + interactive Lamine Yamal shot map (real season data).
   Each shot draws a path to goal + a marker sized by xG, styled by outcome:
     goal = team colour · on target = solid · off target = hollow · blocked = black
   Page content is fully visible without JS; this only adds enhancements.
   =========================================================================== */
(function () {
  "use strict";

  /* Set your LinkedIn URL here to activate the LinkedIn link: */
  var LINKEDIN_URL = "https://www.linkedin.com/in/ram-shiri-1a1056304/";

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var NS = "http://www.w3.org/2000/svg";
  var GOAL_X = 340, GOAL_Y = 30;    // goal-mouth centre (top-centre) in the SVG's coord space
  var GOAL_SCALE = 6.4;             // SVG px per WhoScored goalMouthY unit (640px pitch width / 100):
                                    // gy 50 → x 340 (centre), gy 45/55 → x 308/372 (posts)

  var y = $("#year"); if (y) y.textContent = new Date().getFullYear();
  if (LINKEDIN_URL) $$("[data-linkedin]").forEach(function (a) { a.href = LINKEDIN_URL; });

  /* ---- theme toggle (dark by default; choice saved per visitor) ---- */
  var themeBtn = $("#themeToggle");
  var setThemeIcon = function () {
    var dark = document.documentElement.getAttribute("data-theme") !== "light";
    if (themeBtn) {
      themeBtn.textContent = dark ? "☀️" : "🌙";
      themeBtn.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    }
  };
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var toLight = document.documentElement.getAttribute("data-theme") !== "light";
      document.documentElement.setAttribute("data-theme", toLight ? "light" : "dark");
      try { localStorage.setItem("theme", toLight ? "light" : "dark"); } catch (e) {}
      setThemeIcon();
    });
    setThemeIcon();
  }

  /* ---- sticky nav shadow ---- */
  var nav = $("#nav");
  var onScroll = function () { if (nav) nav.classList.toggle("scrolled", window.scrollY > 8); };
  onScroll(); window.addEventListener("scroll", onScroll, { passive: true });

  /* ---- mobile menu ---- */
  var toggle = $("#navToggle"), links = $("#navLinks");
  if (toggle && links) {
    var close = function () { links.classList.remove("open"); toggle.setAttribute("aria-expanded", "false"); };
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    $$("a", links).forEach(function (a) { a.addEventListener("click", close); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
  }

  /* ---- scrollspy ---- */
  var anchors = $$('.nav-links > a[href^="#"]'), map = {};
  anchors.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
  var secs = $$("main section[id]");
  if ("IntersectionObserver" in window && secs.length) {
    var spy = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        var a = map[e.target.id]; if (!a) return;
        if (e.isIntersecting) { anchors.forEach(function (x) { x.classList.remove("active"); }); a.classList.add("active"); }
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    secs.forEach(function (s) { spy.observe(s); });
  }

  /* =========================================================================
     Lamine Yamal - xG shot map.
     Real 2025/26 shots aggregated from WhoScored match data
     (assets/data/yamal_shots.json). xG is a geometry-based model estimate.
     out ∈ {goal, saved (on target), off, blocked}.
     gy = WhoScored goalMouthY (0–100) where the ball crossed the line: 50 = centre,
     ≈45/≈55 = posts. Optional - without it a path fans out to a stable, outcome-aware
     spot (see goalEndX) so shots don't all stack on the goal centre.
     ========================================================================= */
  var FALLBACK = [
    { x: 560, y: 222, xg: 0.34, min: 38, out: "goal",    body: "Right foot", note: "", situ: "Open play", gy: 46.5 },
    { x: 512, y: 150, xg: 0.05, min: 21, out: "goal",    body: "Left foot",  note: "", situ: "Open play", gy: 53   },
    { x: 470, y: 250, xg: 0.06, min: 12, out: "saved",   body: "Left foot",  note: "", situ: "Open play", gy: 48   },
    { x: 505, y: 300, xg: 0.04, min: 60, out: "off",     body: "Left foot",  note: "", situ: "Open play", gy: 58   },
    { x: 540, y: 205, xg: 0.09, min: 71, out: "blocked", body: "Right foot", note: "", situ: "Open play", gy: 44   }
  ];

  var pathLayer = $("#pathLayer"), layer = $("#shotLayer"), tip = $("#tooltip"), caption = $("#shotTip");
  if (!layer) return;

  var radius = function (xg) { return Math.max(3, Math.min(14, 3.5 + xg * 12)); };
  var showTip = function (h, x, yy) {
    if (!tip) return;
    tip.innerHTML = h; tip.classList.add("show");
    var pad = 14, w = tip.offsetWidth, ht = tip.offsetHeight;
    tip.style.left = Math.min(x + pad, window.innerWidth - w - 8) + "px";
    tip.style.top = Math.max(8, yy - ht - pad) + "px";
  };
  var hideTip = function () { if (tip) tip.classList.remove("show"); };
  var OUT_LABEL = { goal: "Goal ⚽", saved: "On target", off: "Off target", blocked: "Blocked" };
  var vs = function (s) { return s.note ? "vs " + s.note : "Shot"; };
  var tipHtml = function (s) {
    return "<b>" + vs(s) + "</b><br>" + s.min + "' · " + s.body + " · " + s.situ +
           "<br><span class='tt-x'>xG " + Number(s.xg).toFixed(2) + "</span> · " + OUT_LABEL[s.out];
  };
  var setCaption = function (s) {
    if (!caption) return;
    caption.textContent = s.min + "' " + vs(s) + " · " + s.situ + " · " + OUT_LABEL[s.out] + " · xG " + Number(s.xg).toFixed(2);
    caption.classList.add("show");
  };

  // --- where a shot's path ends on the goal line ---------------------------
  // Prefer the measured WhoScored goalMouthY (s.gy). Without it, derive a
  // STABLE, outcome-aware spot so paths fan out naturally instead of all
  // stacking on the goal centre. Add a real gy later and it overrides exactly.
  var hash01 = function (s) {                  // stable pseudo-random [0,1) per shot
    var h = Math.sin(s.x * 12.9898 + s.y * 78.233 + s.min * 37.719) * 43758.5453;
    return h - Math.floor(h);
  };
  var goalEndX = function (s) {
    if (typeof s.gy === "number") return GOAL_X + (s.gy - 50) * GOAL_SCALE;
    var jit = hash01(s) - 0.5;                 // −0.5..0.5
    if (s.out === "off") {                      // missed: end wide of a post
      var side = (s.x >= GOAL_X) ? 1 : -1;
      return GOAL_X + side * (42 + Math.abs(jit) * 26);
    }
    var lean = (s.x - GOAL_X) / 40;            // gentle pull toward the shot's side
    var x = GOAL_X + lean + jit * 50;          // on target/blocked: fill most of the mouth
    return Math.max(311, Math.min(369, x));    // keep just inside the posts (308 / 372)
  };

  var makePath = function (s) {
    var ex = goalEndX(s), ey = GOAL_Y;
    if (s.out === "blocked") {                  // blocked en route - stop short of goal
      ex = s.x + (ex - s.x) * 0.6;
      ey = s.y + (ey - s.y) * 0.6;
    }
    var ln = document.createElementNS(NS, "line");
    ln.setAttribute("x1", s.x); ln.setAttribute("y1", s.y);
    ln.setAttribute("x2", ex); ln.setAttribute("y2", ey);
    ln.setAttribute("class", "shot-path " + s.out);
    return ln;
  };

  var makeDot = function (s, line) {
    var c = document.createElementNS(NS, "circle");
    c.setAttribute("cx", s.x); c.setAttribute("cy", s.y); c.setAttribute("r", radius(s.xg));
    c.setAttribute("class", "shot " + s.out);
    c.setAttribute("tabindex", "0"); c.setAttribute("role", "img");
    c.setAttribute("aria-label", vs(s) + ", " + s.min + " min, " + OUT_LABEL[s.out] + ", xG " + Number(s.xg).toFixed(2));
    var enter = function (ev) {
      c.classList.add("active"); if (line) line.classList.add("lit"); setCaption(s);
      var p = ("touches" in ev && ev.touches[0]) ? ev.touches[0] : ev;
      if (p && p.clientX != null && (p.clientX || p.clientY)) showTip(tipHtml(s), p.clientX, p.clientY);
      else { var r = c.getBoundingClientRect(); showTip(tipHtml(s), r.left + r.width / 2, r.top); }
    };
    var leave = function () { c.classList.remove("active"); if (line) line.classList.remove("lit"); hideTip(); };
    c.addEventListener("mouseenter", enter);
    c.addEventListener("mousemove", function (ev) { showTip(tipHtml(s), ev.clientX, ev.clientY); });
    c.addEventListener("mouseleave", leave);
    c.addEventListener("focus", enter);
    c.addEventListener("blur", leave);
    c.addEventListener("click", function (ev) { ev.preventDefault(); enter(ev); });
    return c;
  };

  var render = function (shots) {
    [pathLayer, layer].forEach(function (g) { if (g) while (g.firstChild) g.removeChild(g.firstChild); });
    // draw non-goals first, goals last, so goals sit on top in both layers
    var ordered = shots.filter(function (s) { return s.out !== "goal"; })
                       .concat(shots.filter(function (s) { return s.out === "goal"; }));
    ordered.forEach(function (s) {
      var line = null;
      if (pathLayer) { line = makePath(s); pathLayer.appendChild(line); }
      layer.appendChild(makeDot(s, line));
    });

    var goals = shots.filter(function (s) { return s.out === "goal"; }).length;
    var xgSum = shots.reduce(function (a, s) { return a + Number(s.xg); }, 0);
    var stats = $("#shotStats");
    if (stats) {
      stats.innerHTML =
        "<div class='st'><b>" + shots.length + "</b><span>Shots</span></div>" +
        "<div class='st'><b>" + goals + "</b><span>Goals</span></div>" +
        "<div class='st'><b>" + xgSum.toFixed(1) + "</b><span>Total xG</span></div>";
    }
  };

  document.addEventListener("click", function (e) {
    if (!e.target.closest || !e.target.closest(".shot, .takeon")) hideTip();
  });

  fetch("assets/data/yamal_shots.json?v=4", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
    .then(function (data) { render(Array.isArray(data) && data.length ? data : FALLBACK); })
    .catch(function () { render(FALLBACK); });

  /* =========================================================================
     Lamine Yamal - take-on map (assets/data/yamal_takeons.json).
     won (beat his marker) vs failed. Toggle buttons show/hide each category.
     ========================================================================= */
  (function () {
    var tkLayer = $("#takeonLayer"), tkArrows = $("#takeonArrows"), tkSvg = $("#takeonmap");
    if (!tkLayer || !tkSvg) return;
    var tkTip = function (p, cat) {
      return "<b>" + (p.opp ? "vs " + p.opp : "Take-on") + "</b><br>" + p.min + "' · " +
             (cat === "won" ? "<span class='tt-x'>Won</span>" : "Failed") + " take-on";
    };
    var dot = function (p, cat) {
      var c = document.createElementNS(NS, "circle");
      c.setAttribute("cx", p.x); c.setAttribute("cy", p.y);
      c.setAttribute("r", cat === "won" ? 4.6 : 4);
      c.setAttribute("class", "takeon " + cat);
      c.setAttribute("tabindex", "0"); c.setAttribute("role", "img");
      c.setAttribute("aria-label", (p.opp ? "vs " + p.opp + ", " : "") + p.min + " min, " + (cat === "won" ? "won" : "failed") + " take-on");
      var enter = function (ev) {
        c.classList.add("active");
        var q = ("touches" in ev && ev.touches[0]) ? ev.touches[0] : ev;
        if (q && q.clientX != null && (q.clientX || q.clientY)) showTip(tkTip(p, cat), q.clientX, q.clientY);
        else { var r = c.getBoundingClientRect(); showTip(tkTip(p, cat), r.left + r.width / 2, r.top); }
      };
      c.addEventListener("mouseenter", enter);
      c.addEventListener("mousemove", function (ev) { showTip(tkTip(p, cat), ev.clientX, ev.clientY); });
      c.addEventListener("mouseleave", function () { c.classList.remove("active"); hideTip(); });
      c.addEventListener("focus", enter);
      c.addEventListener("blur", function () { c.classList.remove("active"); hideTip(); });
      c.addEventListener("click", function (ev) { ev.preventDefault(); enter(ev); });
      return c;
    };
    var arrow = function (p) {
      var ln = document.createElementNS(NS, "line");
      ln.setAttribute("x1", p.x); ln.setAttribute("y1", p.y);
      ln.setAttribute("x2", p.ex); ln.setAttribute("y2", p.ey);
      ln.setAttribute("class", "tk-arrow"); ln.setAttribute("marker-end", "url(#tkArrow)");
      return ln;
    };
    var renderTk = function (data) {
      var won = (data && data.won) || [], failed = (data && data.failed) || [];
      [tkLayer, tkArrows].forEach(function (g) { if (g) while (g.firstChild) g.removeChild(g.firstChild); });
      won.forEach(function (p) { if (tkArrows && p.ex != null && p.ey != null) tkArrows.appendChild(arrow(p)); });
      failed.forEach(function (p) { tkLayer.appendChild(dot(p, "failed")); });
      won.forEach(function (p) { tkLayer.appendChild(dot(p, "won")); });   // won on top
      var total = won.length + failed.length;
      var rate = total ? Math.round(100 * won.length / total) : 0;
      var stats = $("#takeonStats");
      if (stats) stats.innerHTML =
        "<div class='st'><b>" + won.length + "</b><span>Won</span></div>" +
        "<div class='st'><b>" + failed.length + "</b><span>Failed</span></div>" +
        "<div class='st'><b>" + rate + "%</b><span>Success</span></div>";
    };
    $$("#takeonToggles .toggle-chip").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var cat = btn.getAttribute("data-cat");
        var on = btn.getAttribute("aria-pressed") === "false";  // becomes ON
        btn.setAttribute("aria-pressed", on ? "true" : "false");
        tkSvg.classList.toggle("hide-" + cat, !on);
      });
    });
    fetch("assets/data/yamal_takeons.json?v=2", { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
      .then(renderTk)
      .catch(function () {});
  })();

  /* =========================================================================
     Match Centre - Argentina vs Algeria (assets/data/arg_alg_match.json).
     Native rebuild of my WC2026 match centre: scoreboard, head-to-head stat
     bars, a two-team shot map, and animated pass-by-pass goal replays.
     Pitch space: inner rect x 18..682, y 18..422 (same as the take-on map).
     Data coords are 0-100 along/across the pitch; home attacks left -> right.
     ========================================================================= */
  (function () {
    var scoreEl = $("#mcScore"), statsEl = $("#mcStats"),
        shotLayerMc = $("#mcShotLayer"), shotLegend = $("#mcShotLegend"), shotCaption = $("#mcShotTip"),
        tabsEl = $("#mcGoalTabs"), playBtn = $("#mcPlay"),
        replaySvg = $("#mcReplay"), replayLayer = $("#mcReplayLayer"),
        replayDir = $("#mcReplayDir"), replayMeta = $("#mcReplayMeta");
    if (!scoreEl || !shotLayerMc || !replayLayer) return;

    var X0 = 18, Y0 = 18, PW = 664, PH = 404;          // inner pitch rect (px)
    var UNIT = PW / 100;                                // px per data unit
    var MAX_SEG = 52 * UNIT;                            // hide glitched cross-pitch spans
    var tx = function (side, x) { return side === "home" ? X0 + x * PW / 100 : X0 + (100 - x) * PW / 100; };
    var ty = function (side, y) { return side === "home" ? Y0 + (100 - y) * PH / 100 : Y0 + y * PH / 100; };
    var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
    var E = function (n, a) { var e = document.createElementNS(NS, n); if (a) for (var k in a) e.setAttribute(k, a[k]); return e; };
    var fmtDate = function (iso) {
      var d = new Date(iso + "T12:00:00");
      return isNaN(d) ? iso : d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
    };

    /* ---- scoreboard + goals ---- */
    var renderScore = function (D) {
      var goalsFor = function (side) {
        return D.goals.filter(function (g) { return g.team === side; })
          .map(function (g) { return esc(g.scorer) + " " + g.min + "'" + (g.pen ? " (p)" : "") + (g.own ? " (og)" : ""); }).join(" · ");
      };
      scoreEl.innerHTML =
        '<div class="mc-row">' +
          '<div class="mc-team home"><i style="background:' + D.home.color + '"></i>' + esc(D.home.name) + "</div>" +
          '<div class="mc-num">' + D.home.score + " - " + D.away.score + "</div>" +
          '<div class="mc-team away">' + esc(D.away.name) + '<i style="background:' + D.away.color + '"></i></div>' +
        "</div>" +
        '<div class="mc-row mc-scorers">' +
          '<div class="mc-team home">⚽ ' + (goalsFor("home") || "-") + "</div>" +
          '<div class="mc-num sm">xG ' + D.xg[0].toFixed(2) + " - " + D.xg[1].toFixed(2) + "</div>" +
          '<div class="mc-team away">' + (goalsFor("away") ? "⚽ " + goalsFor("away") : "") + "</div>" +
        "</div>" +
        '<div class="mc-meta">' + esc(D.stage) + " · " + esc(D.venue) + " · " + fmtDate(D.date) + "</div>";
    };

    /* ---- head-to-head stat bars ---- */
    var renderStats = function (D) {
      statsEl.innerHTML = D.stats.map(function (s) {
        var h = Number(s.h), a = Number(s.a), tot = (h + a) || 1;
        var vh = s.fmt === "pct" ? h + "%" : (s.fmt === "dec" ? h.toFixed(2) : h);
        var va = s.fmt === "pct" ? a + "%" : (s.fmt === "dec" ? a.toFixed(2) : a);
        return '<div class="mc-stat">' +
          '<div class="mc-stat-line"><b class="' + (h >= a ? "lead" : "") + '">' + vh + "</b><span>" + esc(s.label) + '</span><b class="' + (a > h ? "lead" : "") + '">' + va + "</b></div>" +
          '<div class="mc-bar"><i class="h" style="width:' + (100 * h / tot).toFixed(1) + '%;background:' + D.home.color + '"></i>' +
          '<i class="a" style="width:' + (100 * a / tot).toFixed(1) + '%;background:' + D.away.color + '"></i></div>' +
        "</div>";
      }).join("");
    };

    /* ---- shot map (both teams, opposite directions) ---- */
    var OUTC = function (s) { return s.goal ? "goal" : s.blocked ? "blocked" : s.onTarget ? "on" : "off"; };
    var OUT_TXT = { goal: "Goal ⚽", on: "On target", off: "Off target", blocked: "Blocked" };
    var mcRadius = function (xg) { return Math.max(4, Math.min(15, 4 + xg * 15)); };
    // stable per-shot [0,1) so paths fan out to DIFFERENT spots on the goal line
    var mcHash = function (s) { var h = Math.sin(s.x * 12.9898 + s.y * 78.233 + (s.min + 1) * 37.719) * 43758.5453; return h - Math.floor(h); };
    // across-goal endpoint (data-y 0-100): on-target/goals land between the posts
    // (each at a different point), off-target fan wide of them so they clearly miss.
    var mcGoalY = function (s) {
      if (typeof s.gy === "number") return s.gy;               // real goal-mouth crossing
      var f = mcHash(s) - 0.5;                                  // fallback: outcome-aware fan
      if (OUTC(s) === "off") return 50 + (f >= 0 ? 1 : -1) * (7 + Math.abs(f) * 11);
      return Math.max(45, Math.min(55, 50 + (s.y - 50) / 6 + f * 9));
    };
    var renderShots = function (D) {
      while (shotLayerMc.firstChild) shotLayerMc.removeChild(shotLayerMc.firstChild);
      if (shotCaption) { shotCaption.textContent = esc(D.home.name) + " attack → · ← " + esc(D.away.name) + " attack. Tap or hover a shot."; shotCaption.classList.remove("show"); }
      var name = { home: D.home.name, away: D.away.name };
      // shot-path lines to the attacked goal (drawn first, behind the dots): goals
      // get a prominent team-coloured line, other shots stay faint — like the
      // Lamine Yamal xG shot map. Endpoints fan across the goal via mcGoalY().
      D.shots.forEach(function (s) {
        shotLayerMc.appendChild(E("line", {
          x1: tx(s.team, s.x).toFixed(1), y1: ty(s.team, s.y).toFixed(1),
          x2: tx(s.team, 100).toFixed(1), y2: ty(s.team, mcGoalY(s)).toFixed(1),
          "class": "mc-shotpath " + s.team + " " + OUTC(s)
        }));
      });
      var ordered = D.shots.filter(function (s) { return !s.goal; }).concat(D.shots.filter(function (s) { return s.goal; }));
      ordered.forEach(function (s) {
        var out = OUTC(s);
        var c = E("circle", {
          cx: tx(s.team, s.x).toFixed(1), cy: ty(s.team, s.y).toFixed(1), r: mcRadius(s.xg),
          "class": "mc-shot " + s.team + " " + out, tabindex: "0", role: "img",
          "aria-label": s.player + " (" + name[s.team] + "), " + s.min + " min, " + OUT_TXT[out] + ", xG " + s.xg.toFixed(2)
        });
        var html = "<b>" + esc(s.player) + "</b> · " + esc(name[s.team]) + "<br>" + s.min + "' · " + esc(s.body) + " · " + esc(s.sit) +
                   "<br><span class='tt-x'>xG " + s.xg.toFixed(2) + "</span> · " + OUT_TXT[out];
        var enter = function (ev) {
          c.classList.add("active");
          if (shotCaption) { shotCaption.textContent = s.min + "' " + s.player + " (" + name[s.team] + ") · " + OUT_TXT[out] + " · xG " + s.xg.toFixed(2); shotCaption.classList.add("show"); }
          var p = ("touches" in ev && ev.touches[0]) ? ev.touches[0] : ev;
          if (p && p.clientX != null && (p.clientX || p.clientY)) showTip(html, p.clientX, p.clientY);
          else { var r = c.getBoundingClientRect(); showTip(html, r.left + r.width / 2, r.top); }
        };
        c.addEventListener("mouseenter", enter);
        c.addEventListener("mousemove", function (ev) { showTip(html, ev.clientX, ev.clientY); });
        c.addEventListener("mouseleave", function () { c.classList.remove("active"); hideTip(); });
        c.addEventListener("focus", enter);
        c.addEventListener("blur", function () { c.classList.remove("active"); hideTip(); });
        c.addEventListener("click", function (ev) { ev.preventDefault(); enter(ev); });
        shotLayerMc.appendChild(c);
      });
      if (shotLegend) shotLegend.innerHTML =
        '<span><i class="lg-mc-h"></i> ' + esc(D.home.name) + "</span>" +
        '<span><i class="lg-mc-a"></i> ' + esc(D.away.name) + "</span>" +
        '<span><i class="lg-mc-goal"></i> Goal (white ring)</span>' +
        '<span><i class="lg-mc-off"></i> Off target (hollow)</span>' +
        '<span><i class="lg-mc-path"></i> shot path → goal</span>' +
        '<span class="lg-size"><i></i><i></i><i></i> size = xG</span>';
    };

    /* ---- goal replays: ball travels the real build-up ---------------------
       steps come pre-extracted from the pipeline (same sequence logic as the
       WC2026 dashboard). Node = touch; pass = dotted; carry = dashed; shot =
       solid red into the goal mouth. Play animates the ball along each move. */
    var segD = function (m) {
      if (m.type === "cross") {
        var dx = m.x2 - m.x1, dy = m.y2 - m.y1, len = Math.hypot(dx, dy) || 1, off = Math.min(7 * UNIT, len * 0.2);
        var cx = (m.x1 + m.x2) / 2 + (-dy / len) * off, cy = (m.y1 + m.y2) / 2 + (dx / len) * off;
        return "M" + m.x1.toFixed(1) + "," + m.y1.toFixed(1) + " Q" + cx.toFixed(1) + "," + cy.toFixed(1) + " " + m.x2.toFixed(1) + "," + m.y2.toFixed(1);
      }
      return "M" + m.x1.toFixed(1) + "," + m.y1.toFixed(1) + " L" + m.x2.toFixed(1) + "," + m.y2.toFixed(1);
    };
    var clamp = function (v, a, b) { return Math.max(a, Math.min(b, v)); };
    var segTip = function (kind, opt) {
      if (kind === "pass") return "<b>Pass</b><br>from " + esc(opt.by);
      if (kind === "cross") return "<b>Cross</b><br>from " + esc(opt.by);
      if (kind === "carry") return "<b>Carry / dribble</b>" + (opt.to ? "<br>to " + esc(opt.to) : "");
      return "<b>Shot</b><br>" + esc(opt.by) + (opt.xg != null ? " · xG " + opt.xg.toFixed(2) : "");
    };
    var nodeTip = function (pt, i, seq) {
      var who = "<b>" + esc(pt.player) + (pt.num != null ? " · #" + pt.num : "") + "</b><br>";
      if (pt.k === "save") return who + "Goalkeeper save";
      if (pt.k === "shot") return who + "⚽ Goal" + (pt.xg != null ? " · xG " + pt.xg.toFixed(2) : "") + " · " + seq.min + "'";
      if (pt.k === "shot_eff") return who + "Shot saved" + (pt.xg != null ? " · xG " + pt.xg.toFixed(2) : "");
      if (pt.k === "dribble") return who + "Take-on / dribble";
      return who + (i === 0 ? "Move start" : "On the ball");
    };
    // Order steps into ball moves: node -(pass)-> pass-end -(carry)-> next node ... -(shot)-> goal
    var journey = function (P, side) {
      var mv = [], i, nx, L;
      for (i = 0; i < P.length; i++) {
        var pt = P[i];
        if (pt.k === "pass") {
          mv.push({ type: pt.cross ? "cross" : "pass", x1: pt.x, y1: pt.y, x2: pt.ex, y2: pt.ey, litNode: null, tip: segTip(pt.cross ? "cross" : "pass", { by: pt.player }) });
          if (i < P.length - 1) {
            nx = P[i + 1]; L = Math.hypot(nx.x - pt.ex, nx.y - pt.ey);
            mv.push({ type: nx.k === "save" ? "shotln" : "carry", x1: pt.ex, y1: pt.ey, x2: nx.x, y2: nx.y, litNode: i + 1,
                      hidden: !(L > UNIT && L <= MAX_SEG),
                      tip: nx.k === "save" ? segTip("shot", { by: pt.player }) : segTip("carry", { to: nx.player }) });
          }
        } else if (i < P.length - 1) {
          nx = P[i + 1]; L = Math.hypot(nx.x - pt.x, nx.y - pt.y);
          mv.push({ type: nx.k === "save" ? "shotln" : "carry", x1: pt.x, y1: pt.y, x2: nx.x, y2: nx.y, litNode: i + 1,
                    hidden: !(L > UNIT && L <= MAX_SEG),
                    tip: nx.k === "save" ? segTip("shot", { by: pt.player, xg: pt.xg }) : segTip("carry", { to: nx.player }) });
        }
      }
      var Lp = P[P.length - 1], gx = tx(side, 99.4), gy = ty(side, 50);
      mv.push({ type: "shot", x1: Lp.x, y1: Lp.y, x2: gx, y2: gy, litNode: null,
                hidden: !(Math.hypot(gx - Lp.x, gy - Lp.y) <= MAX_SEG), tip: segTip("shot", { by: Lp.player, xg: Lp.xg }) });
      mv.forEach(function (m) {
        var len = Math.hypot(m.x2 - m.x1, m.y2 - m.y1) / UNIT;   // back to pitch units for pacing
        if (m.hidden) { m.dur = 160; m.dwell = 0; }
        else if (m.type === "pass" || m.type === "cross") { m.dur = clamp(380 + len * 9, 380, 950); m.dwell = 150; }
        else if (m.type === "shot") { m.dur = 470; m.dwell = 0; }
        else if (m.type === "shotln") { m.dur = 380; m.dwell = 120; }
        else { m.dur = clamp(360 + len * 30, 360, 1500); m.dwell = 220; }  // carries are slower than passes
      });
      return mv;
    };

    var current = null;   // { mv, nodeEls, ball, trail, goalText, cancel }
    var buildReplay = function (seq, D) {
      if (current && current.cancel) current.cancel();
      while (replayLayer.firstChild) replayLayer.removeChild(replayLayer.firstChild);
      var P = seq.steps.map(function (st) {
        var sd = st.team || seq.side;   // saves are recorded in the opposition frame
        return { k: st.k, player: st.player, num: st.num, xg: st.xg, cross: !!st.cross,
                 x: tx(sd, st.x), y: ty(sd, st.y),
                 ex: st.ex != null ? tx(sd, st.ex) : null, ey: st.ey != null ? ty(sd, st.ey) : null };
      });
      // pass end defaults to own spot (keeps journey() simple)
      P.forEach(function (p) { if (p.ex == null) { p.ex = p.x; p.ey = p.y; } });
      var mv = journey(P, seq.side);
      var teamName = seq.side === "home" ? D.home.name : D.away.name;
      if (replayDir) replayDir.textContent = seq.side === "home" ? teamName + " attacking →" : "← " + teamName + " attacking";
      if (replayMeta) replayMeta.textContent = seq.min + "' " + seq.scorer + (seq.assist ? " · assist " + seq.assist : "") +
        (seq.xg != null ? " · xG " + seq.xg.toFixed(2) : "") + " · " + seq.passes + " passes, " + seq.players + " players";

      mv.forEach(function (m) {
        m.len = Math.hypot(m.x2 - m.x1, m.y2 - m.y1); m.el = null;
        if (m.hidden) return;
        var segCls = m.type === "cross" ? "mc-pass mc-cross" : m.type === "pass" ? "mc-pass" : m.type === "carry" ? "mc-carry" : "mc-shotln";
        var p = E("path", { "class": segCls, d: segD(m),
                            "marker-end": "url(#" + (m.type === "shot" || m.type === "shotln" ? "mcArrShot" : "mcArrPass") + ")" });
        replayLayer.appendChild(p); m.el = p; m.len = p.getTotalLength();
        var hit = E("path", { "class": "mc-hit", d: segD(m), "data-tip": encodeURIComponent(m.tip) });
        replayLayer.appendChild(hit);
      });
      var nodeEls = P.map(function (pt, i) {
        var cls = pt.k === "save" ? " save" : pt.k === "shot" ? " shot" : pt.k === "shot_eff" ? " shot" : pt.k === "dribble" ? " drib" : (i === 0 ? " start" : "");
        var g = E("g", { "data-tip": encodeURIComponent(nodeTip(pt, i, seq)), "class": "mc-nodeg" });
        g.appendChild(E("circle", { "class": "mc-node" + cls, cx: pt.x.toFixed(1), cy: pt.y.toFixed(1), r: 9 }));
        var t = E("text", { "class": "mc-nt", x: pt.x.toFixed(1), y: pt.y.toFixed(1) });
        t.textContent = pt.num != null ? pt.num : (i + 1);
        g.appendChild(t); replayLayer.appendChild(g); return g;
      });
      // scorer + xG labels above the finishing node
      var Lp = P[P.length - 1], ly = Math.max(30, Lp.y - 14);
      var lab = E("text", { "class": "mc-scorelab", x: Lp.x.toFixed(1), y: (ly - 12).toFixed(1), "text-anchor": "middle" });
      lab.textContent = seq.scorer; replayLayer.appendChild(lab);
      if (seq.xg != null) {
        var lab2 = E("text", { "class": "mc-xglab", x: Lp.x.toFixed(1), y: ly.toFixed(1), "text-anchor": "middle" });
        lab2.textContent = "xG " + seq.xg.toFixed(2); replayLayer.appendChild(lab2);
      }
      var trail = E("polyline", { "class": "mc-trail", points: "" }); replayLayer.appendChild(trail);
      var ball = E("circle", { "class": "mc-ball", cx: P[0].x.toFixed(1), cy: P[0].y.toFixed(1), r: 6.5 });
      ball.style.opacity = "0"; replayLayer.appendChild(ball);
      var gEnd = mv[mv.length - 1];
      var goalText = E("text", { "class": "mc-goalflash", x: (seq.side === "home" ? gEnd.x2 - 66 : gEnd.x2 + 66).toFixed(1), y: Math.max(40, gEnd.y2 - 46).toFixed(1), "text-anchor": "middle" });
      goalText.textContent = "Goal!"; goalText.style.opacity = "0"; replayLayer.appendChild(goalText);

      current = {
        mv: mv, nodeEls: nodeEls, ball: ball, trail: trail, goalText: goalText, P: P, cancel: null,
        rest: function () {
          if (current.cancel) { current.cancel(); current.cancel = null; }
          mv.forEach(function (m) { if (m.el) m.el.style.opacity = "1"; });
          nodeEls.forEach(function (g) { g.style.opacity = "1"; });
          ball.style.opacity = "0"; trail.setAttribute("points", ""); goalText.style.opacity = "0";
        },
        play: function () {
          current.rest();
          mv.forEach(function (m) { if (m.el) m.el.style.opacity = "0.14"; });
          nodeEls.forEach(function (g, i) { g.style.opacity = i === 0 ? "1" : "0.25"; });
          goalText.style.opacity = "0";
          ball.style.opacity = "1"; ball.setAttribute("cx", P[0].x.toFixed(1)); ball.setAttribute("cy", P[0].y.toFixed(1));
          var i = 0, t0 = performance.now(), arrived = false, pts = [], raf;
          var SPEED = 1.15;
          var step = function (now) {
            var m = mv[i], dur = Math.max(60, m.dur / SPEED), e = now - t0, f = Math.min(e, dur) / dur;
            var pos = m.el ? m.el.getPointAtLength(f * m.len) : { x: m.x1 + (m.x2 - m.x1) * f, y: m.y1 + (m.y2 - m.y1) * f };
            if (m.el) m.el.style.opacity = "1";
            ball.setAttribute("cx", pos.x.toFixed(1)); ball.setAttribute("cy", pos.y.toFixed(1));
            pts.push(pos.x.toFixed(1) + "," + pos.y.toFixed(1)); if (pts.length > 16) pts.shift();
            trail.setAttribute("points", pts.join(" "));
            if (e >= dur && !arrived) {
              arrived = true;
              if (m.litNode != null && nodeEls[m.litNode]) nodeEls[m.litNode].style.opacity = "1";
              if (m.el) m.el.style.opacity = "0.6";
            }
            if (e >= dur + (m.dwell || 0) / SPEED) {
              i++; arrived = false; t0 = now;
              if (i >= mv.length) {
                goalText.style.opacity = "1"; current.cancel = null;
                if (playBtn) playBtn.textContent = "↻ Replay";
                return;
              }
            }
            raf = requestAnimationFrame(step);
          };
          raf = requestAnimationFrame(step);
          current.cancel = function () { cancelAnimationFrame(raf); };
        }
      };
      current.rest();
    };

    /* delegated hover tips for replay segments + nodes */
    if (replaySvg) {
      replaySvg.addEventListener("mousemove", function (e) {
        var t = e.target && e.target.closest ? e.target.closest("[data-tip]") : null;
        if (t) showTip(decodeURIComponent(t.getAttribute("data-tip")), e.clientX, e.clientY);
        else hideTip();
      });
      replaySvg.addEventListener("mouseleave", hideTip);
    }

    var renderReplays = function (D) {
      tabsEl.innerHTML = "";
      if (!D.replays.length) {
        if (playBtn) playBtn.disabled = true;
        if (replayDir) replayDir.textContent = "";
        while (replayLayer.firstChild) replayLayer.removeChild(replayLayer.firstChild);
        if (replayMeta) replayMeta.textContent = "No goals in this match.";
        return;
      }
      if (playBtn) playBtn.disabled = false;
      var select = function (i) {
        $$(".toggle-chip", tabsEl).forEach(function (b, j) { b.setAttribute("aria-pressed", j === i ? "true" : "false"); });
        if (playBtn) playBtn.textContent = "▶ Play";
        buildReplay(D.replays[i], D);
      };
      D.replays.forEach(function (r, i) {
        var b = document.createElement("button");
        b.className = "toggle-chip mc-goaltab";
        b.setAttribute("aria-pressed", i === 0 ? "true" : "false");
        var who = r.own ? "OG " + esc((r.ogBy || "").split(" ").pop()) : esc(r.scorer.split(" ").pop());
        b.innerHTML = "⚽ " + r.min + "' " + who;
        b.addEventListener("click", function () { select(i); });
        tabsEl.appendChild(b);
      });
      select(0);
    };

    // Play button is wired once; it always drives the current replay.
    if (playBtn) playBtn.addEventListener("click", function () {
      if (current) { playBtn.textContent = "↻ Replay"; current.play(); }
    });

    /* ---- render one match ---- */
    var renderMatch = function (D) {
      renderScore(D); renderStats(D); renderShots(D); renderReplays(D);
    };

    /* ---- match picker: load the Argentina index, build tabs, swap matches ---- */
    var matchTabs = $("#mcMatchTabs"), fullLink = $("#mcFullLink");
    var DASH = "https://rshiri.github.io/XWORLDCUPTWIT/wc2026_dashboard/match.html?id=";
    var loadMatch = function (m) {
      if (replayMeta) replayMeta.textContent = "Loading…";
      if (fullLink && m.id) fullLink.href = DASH + encodeURIComponent(m.id);
      fetch(m.file + "?v=1", { cache: "no-cache" })
        .then(function (r) { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
        .then(renderMatch)
        .catch(function () { if (replayMeta) replayMeta.textContent = "Match data could not be loaded."; });
    };
    var mcLabel = function (m) {
      var arg = m.argSide === "home" ? m.home : m.away;
      var opp = m.argSide === "home" ? m.away : m.home;
      var dt = new Date(m.date + "T12:00:00");
      var day = isNaN(dt) ? m.date : dt.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
      return '<b>' + esc(opp.name) + '</b> <span class="mc-mt-score">' + arg.score + "-" + opp.score +
             '</span> <span class="mc-mt-date">' + esc(day) + "</span>";
    };

    fetch("assets/data/argentina/index.json?v=1", { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
      .then(function (idx) {
        var matches = (idx && idx.matches) || [];
        if (!matches.length) throw new Error("no matches");
        var select = function (i) {
          $$(".toggle-chip", matchTabs).forEach(function (b, j) { b.setAttribute("aria-pressed", j === i ? "true" : "false"); });
          loadMatch(matches[i]);
        };
        if (matchTabs) {
          matchTabs.innerHTML = "";
          matches.forEach(function (m, i) {
            var b = document.createElement("button");
            b.className = "toggle-chip mc-matchtab";
            b.setAttribute("role", "tab");
            b.setAttribute("aria-pressed", i === 0 ? "true" : "false");
            b.innerHTML = mcLabel(m);
            b.addEventListener("click", function () { select(i); });
            matchTabs.appendChild(b);
          });
        }
        select(0);
      })
      .catch(function () {
        // Fall back to the original single-match file if the index is unavailable.
        fetch("assets/data/arg_alg_match.json?v=1", { cache: "no-cache" })
          .then(function (r) { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
          .then(renderMatch)
          .catch(function () { if (replayMeta) replayMeta.textContent = "Match data could not be loaded."; });
      });
  })();

  /* -----------------------------------------------------------------------
     F1 race progression - the interactive lap-by-lap bump chart from my
     F1 Visualized dashboard, rebuilt self-contained for one race
     (assets/data/f1_race_progression.json). Each line is a driver, coloured
     by team; the marker + code ride the current lap as you scrub or play.
     Positions are reconstructed grid -> classified finish (the site stores
     lap counts, not per-lap arrays), so at every lap the running cars hold
     unique places 1..k. Port of deriveLapPositions()/buildProgression().
     ----------------------------------------------------------------------- */
  (function () {
    var svg = $("#f1pSvg");
    if (!svg) return;

    var TEAM_COLORS = {
      "mclaren": "#ff8000", "ferrari": "#e8002d",
      "red bull racing": "#3671c6", "red bull": "#3671c6",
      "mercedes": "#27f4d2", "aston martin": "#229971", "alpine": "#0093cc",
      "williams": "#1868db", "racing bulls": "#6692ff", "rb": "#6692ff",
      "visa cash app rb": "#6692ff", "alphatauri": "#2b4562",
      "haas": "#b6babd", "haas f1 team": "#b6babd",
      "kick sauber": "#52e252", "sauber": "#52e252",
      "stake f1 team kick sauber": "#52e252", "alfa romeo": "#b12039",
      "audi": "#26c1a3", "cadillac": "#c9a24b"
    };
    function teamColor(team) {
      if (!team) return "#8a8a95";
      return TEAM_COLORS[String(team).trim().toLowerCase()] || "#8a8a95";
    }
    function svgEl(tag, attrs) {
      var n = document.createElementNS(NS, tag);
      if (attrs) for (var k in attrs) n.setAttribute(k, attrs[k]);
      return n;
    }
    function esc(s) {
      return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
      });
    }

    // Reconstruct per-lap positions from grid + classified finish (approx mode).
    function deriveLapPositions(race) {
      var results = race.results || [];
      var n = results.length || 20;
      var total = race.total_laps || 1;
      results.forEach(function (r) { total = Math.max(total, r.laps || 1); });

      var classified = results.filter(function (r) { return r.pos != null; })
        .slice().sort(function (a, b) { return a.pos - b.pos; });
      var dnf = results.filter(function (r) { return r.pos == null; })
        .slice().sort(function (a, b) { return (b.laps || 0) - (a.laps || 0); });
      var finalPos = {};
      classified.forEach(function (r) { finalPos[r.code] = r.pos; });
      dnf.forEach(function (r, i) { finalPos[r.code] = classified.length + i + 1; });

      var curve = results.map(function (r) {
        var fin = finalPos[r.code] || n;
        return {
          code: r.code, team: r.team, fin: fin,
          grid: (r.grid && r.grid > 0) ? r.grid : fin,
          last: Math.max(1, r.laps || total)
        };
      });

      // At each lap, rank the running cars by their continuous (smoothstep)
      // grid->finish value and hand out distinct places - no two share a slot.
      var pos = {};
      curve.forEach(function (c) { pos[c.code] = []; });
      for (var lap = 1; lap <= total; lap++) {
        var running = [];
        curve.forEach(function (c) {
          if (lap > c.last) { pos[c.code].push(null); return; }
          var t = c.last <= 1 ? 1 : (lap - 1) / (c.last - 1);
          var v = c.grid + (c.fin - c.grid) * (t * t * (3 - 2 * t));
          running.push({ code: c.code, v: v, fin: c.fin, grid: c.grid });
        });
        running.sort(function (a, b) {
          return a.v - b.v || a.fin - b.fin || a.grid - b.grid || (a.code < b.code ? -1 : 1);
        });
        running.forEach(function (d, i) { pos[d.code].push(i + 1); });
      }

      var drivers = curve.map(function (c) {
        return { code: c.code, team: c.team, positions: pos[c.code], fin: c.fin };
      });
      drivers.sort(function (a, b) { return a.fin - b.fin; });
      return { total: total, n: n, drivers: drivers };
    }

    function renderPodium(race) {
      var host = $("#f1pPodium");
      if (!host) return;
      var pod = (race.podium || []).slice(0, 3);
      host.innerHTML = pod.map(function (p) {
        return '<div class="f1p-pod">' +
          '<span class="pos">P' + p.pos + '</span>' +
          '<span class="swatch" style="background:' + teamColor(p.team) + '"></span>' +
          '<span class="who"><b>' + esc(p.name) + '</b><span>' + esc(p.team) + '</span></span>' +
          '</div>';
      }).join("");
    }

    function build(race) {
      renderPodium(race);
      var d = deriveLapPositions(race);
      var total = d.total, n = d.n, drivers = d.drivers;
      var W = 1000, H = 440, padL = 44, padR = 48, padT = 16, padB = 30;
      var plotW = W - padL - padR, plotH = H - padT - padB;
      function xOf(lap) { return padL + (total <= 1 ? 0 : ((lap - 1) / (total - 1)) * plotW); }
      function yOf(p) { return padT + (n <= 1 ? 0 : ((p - 1) / (n - 1)) * plotH); }

      var frag = document.createDocumentFragment();
      for (var p = 1; p <= n; p++) {
        if (p === 1 || p % 5 === 0) {
          frag.appendChild(svgEl("line", { x1: padL, y1: yOf(p), x2: W - padR, y2: yOf(p), "class": "f1p-grid" }));
          var yl = svgEl("text", { x: padL - 8, y: yOf(p) + 3.5, "class": "f1p-axis", "text-anchor": "end" });
          yl.textContent = "P" + p; frag.appendChild(yl);
        }
      }
      var step = total <= 30 ? 5 : 10;
      for (var lap = 1; lap <= total; lap += (lap === 1 ? step - 1 : step)) {
        var xl = svgEl("text", { x: xOf(lap), y: H - padB + 18, "class": "f1p-axis", "text-anchor": "middle" });
        xl.textContent = lap; frag.appendChild(xl);
      }

      var bright = {}, marker = {}, label = {};
      drivers.forEach(function (dr) {
        var color = teamColor(dr.team);
        var pts = [];
        dr.positions.forEach(function (pp, i) { if (pp != null) pts.push(xOf(i + 1) + "," + yOf(pp)); });
        frag.appendChild(svgEl("polyline", { points: pts.join(" "), "class": "f1p-faint", stroke: color }));
        bright[dr.code] = svgEl("polyline", { points: "", "class": "f1p-line", stroke: color });
        frag.appendChild(bright[dr.code]);
      });
      var vline = svgEl("line", { x1: xOf(1), y1: padT, x2: xOf(1), y2: H - padB, "class": "f1p-vline" });
      frag.appendChild(vline);
      drivers.forEach(function (dr) {
        var color = teamColor(dr.team);
        marker[dr.code] = svgEl("circle", { r: 3.4, "class": "f1p-dot", fill: color, cx: -20, cy: -20 });
        frag.appendChild(marker[dr.code]);
        var lab = svgEl("text", { "class": "f1p-code", x: -20, y: -20, fill: color });
        lab.textContent = dr.code; label[dr.code] = lab; frag.appendChild(lab);
      });
      svg.appendChild(frag);

      var slider = $("#f1pSlider"), playBtn = $("#f1pPlay"), lapLabel = $("#f1pLap");
      slider.max = total; slider.value = total;

      function setLap(L) {
        L = Math.max(1, Math.min(total, L | 0));
        vline.setAttribute("x1", xOf(L)); vline.setAttribute("x2", xOf(L));
        slider.value = L;
        if (lapLabel) lapLabel.textContent = "Lap " + L + " / " + total;
        drivers.forEach(function (dr) {
          var pts = [];
          for (var lp = 1; lp <= L; lp++) { var pp = dr.positions[lp - 1]; if (pp != null) pts.push(xOf(lp) + "," + yOf(pp)); }
          bright[dr.code].setAttribute("points", pts.join(" "));
          var cur = dr.positions[L - 1];
          var on = cur != null ? "1" : "0";
          marker[dr.code].style.opacity = on; label[dr.code].style.opacity = on;
          if (cur != null) {
            marker[dr.code].setAttribute("cx", xOf(L)); marker[dr.code].setAttribute("cy", yOf(cur));
            label[dr.code].setAttribute("x", xOf(L) + 6); label[dr.code].setAttribute("y", yOf(cur) + 3.5);
          }
        });
      }

      var timer = null;
      function stop() { if (timer) { clearInterval(timer); timer = null; } if (playBtn) playBtn.textContent = "▶ Play"; }
      function play() {
        stop();
        var L = (+slider.value >= total) ? 1 : +slider.value;
        if (playBtn) playBtn.textContent = "❚❚ Pause";
        timer = setInterval(function () {
          L += 1;
          if (L > total) { setLap(total); stop(); return; }
          setLap(L);
        }, 110);
      }
      slider.addEventListener("input", function () { stop(); setLap(+slider.value); });
      if (playBtn) playBtn.addEventListener("click", function () { timer ? stop() : play(); });

      setLap(total);
    }

    fetch("assets/data/f1_race_progression.json?v=1", { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
      .then(build)
      .catch(function (e) {
        var tip = $("#f1pTip");
        if (tip) tip.textContent = "Race data could not be loaded.";
      });
  })();
})();
