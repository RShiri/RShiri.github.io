/* ===========================================================================
   Ram Shiri — portfolio interactions (dependency-free).
   Nav + scrollspy + interactive Lamine Yamal shot map.
   Page content is fully visible without JS; this only adds enhancements.
   =========================================================================== */
(function () {
  "use strict";

  /* Set your LinkedIn URL here to activate the LinkedIn link: */
  var LINKEDIN_URL = "";

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var NS = "http://www.w3.org/2000/svg";

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
     Lamine Yamal — xG shot map. Selected shots (illustrative sample).
     Coordinates are in the SVG's 0..700 x 0..440 space; goal is on the right.
     ========================================================================= */
  var SHOTS = [
    { x: 512, y: 150, xg: 0.05, min: 21, out: "goal",    body: "Left foot",  note: "Curler into the top corner" },
    { x: 560, y: 222, xg: 0.34, min: 38, out: "goal",    body: "Right foot", note: "Cutback finish" },
    { x: 470, y: 250, xg: 0.06, min: 12, out: "saved",   body: "Left foot",  note: "Low drive from the edge" },
    { x: 600, y: 198, xg: 0.52, min: 64, out: "goal",    body: "Right foot", note: "Close-range finish" },
    { x: 400, y: 210, xg: 0.03, min: 5,  out: "off",     body: "Left foot",  note: "Speculative long shot" },
    { x: 525, y: 300, xg: 0.11, min: 71, out: "off",     body: "Left foot",  note: "Angled effort, wide" },
    { x: 505, y: 135, xg: 0.07, min: 44, out: "saved",   body: "Left foot",  note: "Cut in from the right" },
    { x: 548, y: 222, xg: 0.76, min: 80, out: "goal",    body: "Right foot", note: "Penalty, bottom corner" },
    { x: 462, y: 188, xg: 0.05, min: 29, out: "blocked", body: "Right foot", note: "Blocked inside the box" },
    { x: 588, y: 292, xg: 0.14, min: 55, out: "saved",   body: "Left foot",  note: "Near-post effort" },
    { x: 620, y: 150, xg: 0.09, min: 33, out: "off",     body: "Left foot",  note: "Tight angle, over" },
    { x: 535, y: 205, xg: 0.19, min: 88, out: "goal",    body: "Right foot", note: "Edge of the six-yard box" }
  ];
  var OUT_LABEL = { goal: "Goal ⚽", saved: "Saved", off: "Off target", blocked: "Blocked" };

  var layer = $("#shotLayer"), tip = $("#tooltip"), caption = $("#shotTip");

  if (layer) {
    var radius = function (xg) { return Math.max(6, Math.min(20, 6 + xg * 20)); };

    var showTip = function (html, x, yy) {
      if (!tip) return;
      tip.innerHTML = html; tip.classList.add("show");
      var pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
      var left = Math.min(x + pad, window.innerWidth - w - 8);
      var top = Math.max(8, yy - h - pad);
      tip.style.left = left + "px"; tip.style.top = top + "px";
    };
    var hideTip = function () { if (tip) tip.classList.remove("show"); };
    var html = function (s) {
      return "<b>" + s.note + "</b><br>" + s.min + "' · " + s.body +
             " · <span class='tt-x'>xG " + s.xg.toFixed(2) + "</span> · " + OUT_LABEL[s.out];
    };
    var setCaption = function (s) {
      if (!caption) return;
      caption.textContent = s.min + "' — " + s.note + " · " + OUT_LABEL[s.out] + " · xG " + s.xg.toFixed(2);
      caption.classList.add("show");
    };

    SHOTS.forEach(function (s) {
      var c = document.createElementNS(NS, "circle");
      c.setAttribute("cx", s.x); c.setAttribute("cy", s.y); c.setAttribute("r", radius(s.xg));
      c.setAttribute("class", "shot " + (s.out === "goal" ? "goal" : "miss"));
      c.setAttribute("tabindex", "0");
      c.setAttribute("role", "img");
      c.setAttribute("aria-label", s.note + ", " + OUT_LABEL[s.out] + ", xG " + s.xg.toFixed(2));
      var enter = function (ev) {
        c.classList.add("active"); setCaption(s);
        var p = ("touches" in ev && ev.touches[0]) ? ev.touches[0] : ev;
        if (p && p.clientX != null) showTip(html(s), p.clientX, p.clientY);
        else { var r = c.getBoundingClientRect(); showTip(html(s), r.left + r.width / 2, r.top); }
      };
      c.addEventListener("mouseenter", enter);
      c.addEventListener("mousemove", function (ev) { showTip(html(s), ev.clientX, ev.clientY); });
      c.addEventListener("mouseleave", function () { c.classList.remove("active"); hideTip(); });
      c.addEventListener("focus", enter);
      c.addEventListener("blur", function () { c.classList.remove("active"); hideTip(); });
      c.addEventListener("click", function (ev) { ev.preventDefault(); enter(ev); });
      layer.appendChild(c);
    });

    /* summary stats */
    var goals = SHOTS.filter(function (s) { return s.out === "goal"; }).length;
    var xgSum = SHOTS.reduce(function (a, s) { return a + s.xg; }, 0);
    var stats = $("#shotStats");
    if (stats) {
      stats.innerHTML =
        "<div class='st'><b>" + SHOTS.length + "</b><span>Shots</span></div>" +
        "<div class='st'><b>" + goals + "</b><span>Goals</span></div>" +
        "<div class='st'><b>" + xgSum.toFixed(2) + "</b><span>Total xG</span></div>";
    }

    /* hide tooltip when tapping elsewhere */
    document.addEventListener("click", function (e) {
      if (!e.target.closest || !e.target.closest(".shot")) hideTip();
    });
  }
})();
