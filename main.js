/* ===========================================================================
   Ram Shiri — portfolio interactions (dependency-free).
   Nav + scrollspy + interactive Lamine Yamal shot map (real season data).
   Each shot draws a path to goal + a marker sized by xG, styled by outcome:
     goal = team colour · on target = solid · off target = hollow · blocked = black
   Page content is fully visible without JS; this only adds enhancements.
   =========================================================================== */
(function () {
  "use strict";

  /* Set your LinkedIn URL here to activate the LinkedIn link: */
  var LINKEDIN_URL = "";

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var NS = "http://www.w3.org/2000/svg";
  var GOAL_X = 340, GOAL_Y = 30;    // goal-mouth centre (top-centre) in the SVG's coord space

  var y = $("#year"); if (y) y.textContent = new Date().getFullYear();
  if (LINKEDIN_URL) $$("[data-linkedin]").forEach(function (a) { a.href = LINKEDIN_URL; });

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
     Lamine Yamal — xG shot map.
     Real 2025/26 shots aggregated from WhoScored match data
     (assets/data/yamal_shots.json). xG is a geometry-based model estimate.
     out ∈ {goal, saved (on target), off, blocked}.
     ========================================================================= */
  var FALLBACK = [
    { x: 560, y: 222, xg: 0.34, min: 38, out: "goal",    body: "Right foot", note: "", situ: "Open play" },
    { x: 512, y: 150, xg: 0.05, min: 21, out: "goal",    body: "Left foot",  note: "", situ: "Open play" },
    { x: 470, y: 250, xg: 0.06, min: 12, out: "saved",   body: "Left foot",  note: "", situ: "Open play" },
    { x: 505, y: 300, xg: 0.04, min: 60, out: "off",     body: "Left foot",  note: "", situ: "Open play" },
    { x: 540, y: 205, xg: 0.09, min: 71, out: "blocked", body: "Right foot", note: "", situ: "Open play" }
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

  var makePath = function (s) {
    var ln = document.createElementNS(NS, "line");
    ln.setAttribute("x1", s.x); ln.setAttribute("y1", s.y);
    ln.setAttribute("x2", GOAL_X); ln.setAttribute("y2", GOAL_Y);
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
     Lamine Yamal — take-on map (assets/data/yamal_takeons.json).
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
})();
