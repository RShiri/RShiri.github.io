/* Hebrew for the in-repo explainer pages (xg-model, winprob-model, live-pipeline).
   Each page loads its own content-he.js first, which sets
     window.RS_HE_BLOCKS = [["English block text (or its first 24+ non-space chars)", "Hebrew HTML"], ...]
   plus RS_I18N (short UI strings, also text that the page's JS writes later) and RS_ABOUT.
   This script finds each block by its English text and gives it data-he-html, which the
   brand kit (brand.js) swaps in while Hebrew is on and restores in English.
   Load it at the end of <body>, after the page's own scripts have rendered their markup. */
(function () {
  var B = window.RS_HE_BLOCKS || [];
  if (!B.length) return;
  /* whitespace-free comparison: <br> and line breaks inside a block don't matter */
  function norm(s) { return String(s).replace(/\s+/g, ""); }
  var keys = B.map(function (b) { return norm(b[0]); });
  var exact = {};
  keys.forEach(function (k, i) { if (!(k in exact)) exact[k] = i; });
  var hits = [];
  var all = document.body.getElementsByTagName("*");
  for (var n = 0; n < all.length; n++) {
    var el = all[n];
    if (/^(SCRIPT|STYLE|NOSCRIPT|svg|defs|marker|path|rect|line|circle)$/.test(el.tagName)) continue;
    if (el.closest(".rs-bar, .rs-about")) continue;
    if (el.namespaceURI !== "http://www.w3.org/1999/xhtml") continue;   /* SVG text goes through RS_I18N */
    var t = norm(el.textContent);
    if (!t) continue;
    var idx = exact[t];
    if (idx == null) {
      for (var i = 0; i < keys.length; i++) { if (keys[i].length >= 24 && t.indexOf(keys[i]) === 0) { idx = i; break; } }
    }
    if (idx != null) hits.push([el, idx]);
  }
  /* keep the innermost match: a wrapper whose text equals one child's text is skipped */
  hits = hits.filter(function (h) {
    return !hits.some(function (o) { return o !== h && o[0] !== h[0] && h[0].contains(o[0]); });
  });
  hits.forEach(function (h) { h[0].setAttribute("data-he-html", B[h[1]][1]); });
  if (window.RSBrand && window.RSBrand.refresh) window.RSBrand.refresh();
})();
