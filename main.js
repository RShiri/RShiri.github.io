/* ===========================================================================
   Ram Shiri — portfolio interactions (dependency-free).
   Nav + scrollspy + interactive Lamine Yamal shot map (real season data).
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
     Lamine Yamal — xG shot map.
     Real 2025/26 season shots, aggregated from WhoScored match data
     (assets/data/yamal_shots.json). xG is a geometry-based model estimate.
     Each shot: {x,y} in the SVG's 0..700 x 0..440 space (goal on the right),
     xg, min, out ('goal'|'miss'), body, note (opponent), situ.
     ========================================================================= */
  var FALLBACK = [
    { x: 512, y: 150, xg: 0.05, min: 21, out: "goal", body: "Left foot",  note: "", situ: "Open play" },
    { x: 560, y: 222, xg: 0.34, min: 38, out: "goal", body: "Right foot", note: "", situ: "Open play" },
    { x: 470, y: 250, xg: 0.06, min: 12, out: "miss", body: "Left foot",  note: "", situ: "Open play" },
    { x: 548, y: 222, xg: 0.76, min: 80, out: "goal", body: "Right foot", note: "", situ: "Penalty" },
    { x: 400, y: 210, xg: 0.03, min: 5,  out: "miss", body: "Left foot",  note: "", situ: "Open play" }
  ];

  var layer = $("#shotLayer"), tip = $("#tooltip"), caption = $("#shotTip");
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
  var OUT_LABEL = { goal: "Goal ⚽", miss: "No goal" };
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

  var makeDot = function (s) {
    var c = document.createElementNS(NS, "circle");
    c.setAttribute("cx", s.x); c.setAttribute("cy", s.y); c.setAttribute("r", radius(s.xg));
    c.setAttribute("class", "shot " + (s.out === "goal" ? "goal" : "miss"));
    c.setAttribute("tabindex", "0"); c.setAttribute("role", "img");
    c.setAttribute("aria-label", vs(s) + ", " + s.min + " min, " + OUT_LABEL[s.out] + ", xG " + Number(s.xg).toFixed(2));
    var enter = function (ev) {
      c.classList.add("active"); setCaption(s);
      var p = ("touches" in ev && ev.touches[0]) ? ev.touches[0] : ev;
      if (p && p.clientX != null && (p.clientX || p.clientY)) showTip(tipHtml(s), p.clientX, p.clientY);
      else { var r = c.getBoundingClientRect(); showTip(tipHtml(s), r.left + r.width / 2, r.top); }
    };
    c.addEventListener("mouseenter", enter);
    c.addEventListener("mousemove", function (ev) { showTip(tipHtml(s), ev.clientX, ev.clientY); });
    c.addEventListener("mouseleave", function () { c.classList.remove("active"); hideTip(); });
    c.addEventListener("focus", enter);
    c.addEventListener("blur", function () { c.classList.remove("active"); hideTip(); });
    c.addEventListener("click", function (ev) { ev.preventDefault(); enter(ev); });
    return c;
  };

  var render = function (shots) {
    while (layer.firstChild) layer.removeChild(layer.firstChild);
    // draw misses first, goals on top so they stand out
    var misses = shots.filter(function (s) { return s.out !== "goal"; });
    var goals = shots.filter(function (s) { return s.out === "goal"; });
    misses.concat(goals).forEach(function (s) { layer.appendChild(makeDot(s)); });

    var xgSum = shots.reduce(function (a, s) { return a + Number(s.xg); }, 0);
    var stats = $("#shotStats");
    if (stats) {
      stats.innerHTML =
        "<div class='st'><b>" + shots.length + "</b><span>Shots</span></div>" +
        "<div class='st'><b>" + goals.length + "</b><span>Goals</span></div>" +
        "<div class='st'><b>" + xgSum.toFixed(1) + "</b><span>Total xG</span></div>";
    }
  };

  document.addEventListener("click", function (e) {
    if (!e.target.closest || !e.target.closest(".shot")) hideTip();
  });

  fetch("assets/data/yamal_shots.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
    .then(function (data) { render(Array.isArray(data) && data.length ? data : FALLBACK); })
    .catch(function () { render(FALLBACK); });
})();
