/* Ram Shiri portfolio brand kit, shared by every project site on rshiri.github.io.
   Load it synchronously in <head>:
     <link rel="stylesheet" href="https://rshiri.github.io/assets/brand/brand.css">
     <script src="https://rshiri.github.io/assets/brand/brand.js"></script>

   Look: sets html[data-site-style="c"|"a"] from localStorage "site-style" (shared with the
   portfolio; ?style=a|c in the URL wins and is remembered) and fires "sitestylechange".

   Language: sets html[data-site-lang="en"|"he"] from localStorage "site-lang" (?lang=he|en
   wins) and fires "sitelangchange". Hebrew is opt-in, for readers who prefer it. A project
   gives its Hebrew in one of two ways (both optional, both can be set any time before or
   after this script runs):
     window.RS_I18N = { "Exact English text": "טקסט בעברית", ... }
        Text nodes and title/placeholder/aria-label attributes whose trimmed text matches a key
        are swapped while Hebrew is on (also inside content rendered later), and restored in
        English. Swapped elements get dir="auto" so Hebrew reads right-to-left.
     Elements with data-he="..." swap their textContent the same way; data-he-html="..." swaps
     innerHTML (for paragraphs with inline markup) and sets dir="rtl".
   html[data-rs-nobar] (the portfolio home page) gets the language engine without the bar.
   About panel: window.RS_ABOUT = { en: {title, intro, sections:[{h, p}]}, he: {...} }
     adds an "About this project" button to the bar that opens a detailed explainer
     (p may contain simple HTML). The panel follows the language switch.

   It also adds the portfolio bar (RAM/SHIRI, All projects, About, EN/HE, C/A) at the top
   of <body>. window.RSBrand exposes {style(), lang(), refresh()} for projects. */
(function () {
  var HOME = "https://rshiri.github.io/";
  var root = document.documentElement;

  function pref(key, param, allowed, dflt) {
    var q = new RegExp("[?&]" + param + "=(" + allowed.join("|") + ")\\b").exec(location.search);
    if (q) { try { localStorage.setItem(key, q[1]); } catch (e) {} return q[1]; }
    try { var v = localStorage.getItem(key); return allowed.indexOf(v) >= 0 ? v : dflt; } catch (e) { return dflt; }
  }
  function save(key, v) { try { localStorage.setItem(key, v); } catch (e) {} }

  root.setAttribute("data-site-style", pref("site-style", "style", ["c", "a"], "c"));
  root.setAttribute("data-site-lang", pref("site-lang", "lang", ["en", "he"], "en"));
  var style = function () { return root.getAttribute("data-site-style"); };
  var lang = function () { return root.getAttribute("data-site-lang"); };

  if (!document.querySelector("link[data-rs-fonts]")) {
    var f = document.createElement("link");
    f.rel = "stylesheet"; f.setAttribute("data-rs-fonts", "");
    f.href = "https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Hebrew:wght@400;500;600&family=Barlow+Condensed:ital,wght@0,700;0,800;1,700;1,800&family=Barlow:wght@500;600;700&display=swap";
    document.head.appendChild(f);
  }

  /* ---------------- Hebrew swapping ---------------- */
  var ORIG = "__rsOrig", ATTRS = ["title", "placeholder", "aria-label"];
  var busy = false;
  var WHOLE = "p, li, dd, dt, td, th, h1, h2, h3, h4, h5, label, figcaption, small, .chart-tip, .sub, .lead, .note, .caption, .hint, .desc";
  function dict() { return window.RS_I18N || {}; }
  function swapText(node, d, he) {
    if (he) {
      var src = node[ORIG] != null ? node[ORIG] : node.nodeValue;
      var key = src.trim();
      if (key && Object.prototype.hasOwnProperty.call(d, key)) {
        if (node[ORIG] == null) node[ORIG] = node.nodeValue;
        var nv = src.replace(key, d[key]); if (node.nodeValue !== nv) node.nodeValue = nv;
        if (node.parentElement && !node.parentElement.hasAttribute("dir")) { node.parentElement.setAttribute("dir", "auto"); node.parentElement.setAttribute("data-rs-dir", ""); }
      }
    } else if (node[ORIG] != null) {
      node.nodeValue = node[ORIG]; node[ORIG] = null;
      var p = node.parentElement;
      if (p && p.hasAttribute("data-rs-dir")) { p.removeAttribute("dir"); p.removeAttribute("data-rs-dir"); }
    }
  }
  function swapEl(el, d, he) {
    ATTRS.forEach(function (a) {
      var k = "data-rs-orig-" + a;
      if (he) {
        var src = el.hasAttribute(k) ? el.getAttribute(k) : el.getAttribute(a);
        if (src && Object.prototype.hasOwnProperty.call(d, src.trim())) { if (!el.hasAttribute(k)) el.setAttribute(k, src); el.setAttribute(a, d[src.trim()]); }
      } else if (el.hasAttribute(k)) { el.setAttribute(a, el.getAttribute(k)); el.removeAttribute(k); }
    });
    if (el.hasAttribute("data-he-html")) {
      if (he) { if (el.__rsHtml == null) { el.__rsHtml = el.innerHTML; el.innerHTML = el.getAttribute("data-he-html"); el.setAttribute("dir", "rtl"); } }
      else if (el.__rsHtml != null) { el.innerHTML = el.__rsHtml; el.__rsHtml = null; el.removeAttribute("dir"); }
    }
    if (el.hasAttribute("data-he")) {
      if (he) { if (!el.hasAttribute("data-en")) { el.setAttribute("data-en", el.textContent); el.textContent = el.getAttribute("data-he"); el.setAttribute("dir", "auto"); } }
      else if (el.hasAttribute("data-en")) { el.textContent = el.getAttribute("data-en"); el.removeAttribute("data-en"); el.removeAttribute("dir"); }
    }
  }
  function translate(scope) {
    if (!document.body) return;
    busy = true;
    var d = dict(), he = lang() === "he";
    scope = scope || document.body;
    var w = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        var p = n.parentElement;
        if (!p || /^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA)$/.test(p.tagName) || p.closest(".rs-bar, .rs-about, [data-he], [data-he-html], [data-rs-whole]")) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    /* whole-element match first: paragraphs whose text is split by inline markup
       (<b>, <a>, <code>) match a key on their normalised full text */
    var host = scope.nodeType === 1 ? scope : scope.parentElement;
    if (host) {
      var cands = [host].concat(Array.prototype.slice.call(host.querySelectorAll(WHOLE)));
      cands.forEach(function (el) {
        if (!el.matches || !el.matches(WHOLE) || el.closest(".rs-bar, .rs-about, [data-he], [data-he-html]")) return;
        if (he) {
          if (el.__rsWhole != null || !el.children.length) return;
          /* never flatten controls, media or anything scripts address by id */
          if (el.querySelector("input, select, textarea, button, img, svg, canvas, video, iframe, datalist, [id]")) return;
          var key = el.textContent.replace(/\s+/g, " ").trim();
          if (key && Object.prototype.hasOwnProperty.call(d, key)) {
            el.__rsWhole = el.innerHTML; el.textContent = d[key];
            if (!el.hasAttribute("dir")) { el.setAttribute("dir", "auto"); el.setAttribute("data-rs-dir", ""); }
            el.setAttribute("data-rs-whole", "");
          }
        } else if (el.__rsWhole != null) {
          el.innerHTML = el.__rsWhole; el.__rsWhole = null; el.removeAttribute("data-rs-whole");
          if (el.hasAttribute("data-rs-dir")) { el.removeAttribute("dir"); el.removeAttribute("data-rs-dir"); }
        }
      });
    }
    var n; while ((n = w.nextNode())) swapText(n, d, he);
    if (scope.nodeType === 1) {
      swapEl(scope, d, he);
      scope.querySelectorAll("[title],[placeholder],[aria-label],[data-he],[data-he-html]").forEach(function (el) { if (!el.closest(".rs-bar, .rs-about")) swapEl(el, d, he); });
    }
    busy = false;
  }
  var mo = new MutationObserver(function (muts) {
    if (busy || lang() !== "he") return;
    muts.forEach(function (m) {
      m.addedNodes.forEach(function (n) { if (n.nodeType === 1) translate(n); else if (n.nodeType === 3 && n.parentElement) translate(n.parentElement); });
      if (m.type === "characterData" && m.target.parentElement && m.target[ORIG] == null) translate(m.target.parentElement);
    });
  });

  /* ---------------- About panel ---------------- */
  var UI = {
    en: { back: "All projects", about: "About this project", aboutShort: "About", close: "Close", lang: "עברית", langLabel: "Switch to Hebrew" },
    he: { back: "כל הפרויקטים", about: "על הפרויקט", aboutShort: "אודות", close: "סגירה", lang: "EN", langLabel: "Switch to English" }
  };
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function renderAbout() {
    var box = document.querySelector(".rs-about__body");
    var A = window.RS_ABOUT; if (!box || !A) return;
    var L = A[lang()] || A.en;
    var panel = document.querySelector(".rs-about");
    panel.setAttribute("dir", lang() === "he" ? "rtl" : "ltr");
    panel.setAttribute("lang", lang());
    panel.querySelector(".rs-about__close").textContent = UI[lang()].close;
    box.innerHTML = "<h2>" + esc(L.title || "") + "</h2>" + (L.intro ? '<p class="rs-about__intro">' + L.intro + "</p>" : "") +
      (L.sections || []).map(function (s) { return "<section><h3>" + esc(s.h) + "</h3><p>" + s.p + "</p></section>"; }).join("");
  }
  function openAbout(open) {
    var panel = document.querySelector(".rs-about"); if (!panel) return;
    panel.hidden = !open;
    document.body.classList.toggle("rs-about-open", open);
    if (open) { renderAbout(); panel.querySelector(".rs-about__close").focus(); }
  }

  function refreshBar() {
    var bar = document.querySelector(".rs-bar"); if (!bar) return;
    var u = UI[lang()];
    bar.setAttribute("dir", lang() === "he" ? "rtl" : "ltr");
    bar.querySelector(".rs-bar__back span:last-child").textContent = u.back;
    var ab = bar.querySelector(".rs-bar__about");
    ab.hidden = !window.RS_ABOUT;
    ab.innerHTML = '<span class="rs-long">' + esc(u.about) + '</span><span class="rs-short">' + esc(u.aboutShort) + "</span>";
    var lb = bar.querySelector(".rs-bar__lang"); lb.textContent = u.lang; lb.setAttribute("aria-label", u.langLabel);
    bar.querySelectorAll(".rs-bar__style b").forEach(function (el) { el.classList.toggle("on", el.textContent.toLowerCase() === style()); });
  }
  function setLang(v) {
    root.setAttribute("data-site-lang", v); save("site-lang", v);
    refreshBar(); translate();
    var ap = document.querySelector(".rs-about");
    if (ap && !ap.hidden) renderAbout();
    window.dispatchEvent(new CustomEvent("sitelangchange", { detail: v }));
  }

  function init() {
    if (root.hasAttribute("data-rs-nobar")) { /* the portfolio itself: no bar, just the language engine */
      translate();
      mo.observe(document.body, { childList: true, subtree: true, characterData: true });
      return;
    }
    if (document.querySelector(".rs-bar")) return;
    var bar = document.createElement("div");
    bar.className = "rs-bar";
    bar.innerHTML =
      '<a class="rs-bar__brand" href="' + HOME + '" dir="ltr">RAM<i>/</i>SHIRI</a>' +
      '<a class="rs-bar__back" href="' + HOME + '#builds"><span aria-hidden="true">&larr;</span> <span class="rs-long"></span></a>' +
      '<button class="rs-bar__about" type="button" hidden></button>' +
      '<span class="rs-bar__end"><button class="rs-bar__lang" type="button"></button>' +
      '<button class="rs-bar__style" type="button" aria-label="Switch design" dir="ltr"><b>C</b><span aria-hidden="true">/</span><b>A</b></button></span>';
    document.body.insertBefore(bar, document.body.firstChild);

    var panel = document.createElement("div");
    panel.className = "rs-about"; panel.hidden = true;
    panel.setAttribute("role", "dialog"); panel.setAttribute("aria-modal", "true");
    panel.innerHTML = '<div class="rs-about__scrim"></div><div class="rs-about__sheet"><button class="rs-about__close" type="button"></button><div class="rs-about__body"></div></div>';
    document.body.appendChild(panel);
    panel.querySelector(".rs-about__scrim").addEventListener("click", function () { openAbout(false); });
    panel.querySelector(".rs-about__close").addEventListener("click", function () { openAbout(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !panel.hidden) openAbout(false); });

    bar.querySelector(".rs-bar__about").addEventListener("click", function () { openAbout(true); });
    bar.querySelector(".rs-bar__lang").addEventListener("click", function () { setLang(lang() === "he" ? "en" : "he"); });
    bar.querySelector(".rs-bar__style").addEventListener("click", function () {
      var next = style() === "a" ? "c" : "a";
      root.setAttribute("data-site-style", next); save("site-style", next); refreshBar();
      window.dispatchEvent(new CustomEvent("sitestylechange", { detail: next }));
    });
    refreshBar();
    translate();
    mo.observe(document.body, { childList: true, subtree: true, characterData: true });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
  /* late-arriving dictionaries / about content */
  window.addEventListener("load", function () { refreshBar(); translate(); });

  window.RSBrand = {
    style: style, lang: lang, setLang: setLang,
    refresh: function () { refreshBar(); translate(); if (document.querySelector(".rs-about") && !document.querySelector(".rs-about").hidden) renderAbout(); },
    openAbout: function () { openAbout(true); }
  };
})();
