/* Ram Shiri portfolio brand kit, shared by every project site on rshiri.github.io.
   Load it synchronously in <head>:
     <link rel="stylesheet" href="https://rshiri.github.io/assets/brand/brand.css">
     <script src="https://rshiri.github.io/assets/brand/brand.js"></script>
   It sets html[data-site-style="c"|"a"] from the same localStorage key the portfolio uses
   ("site-style"; ?style=a|c in the URL wins and is remembered), loads the brand fonts and,
   once the page is parsed, adds the portfolio bar at the top of <body>. Project CSS themes
   itself off html[data-site-style] and listens for the "sitestylechange" event if needed. */
(function () {
  var KEY = "site-style", HOME = "https://rshiri.github.io/";
  var root = document.documentElement;
  function read() {
    var q = /[?&]style=([ac])\b/.exec(location.search);
    if (q) { try { localStorage.setItem(KEY, q[1]); } catch (e) {} return q[1]; }
    try { return localStorage.getItem(KEY) === "a" ? "a" : "c"; } catch (e) { return "c"; }
  }
  function apply(v) {
    root.setAttribute("data-site-style", v);
    document.querySelectorAll(".rs-bar__style b").forEach(function (el) { el.classList.toggle("on", el.textContent.toLowerCase() === v); });
  }
  apply(read());

  if (!document.querySelector('link[data-rs-fonts]')) {
    var f = document.createElement("link");
    f.rel = "stylesheet"; f.setAttribute("data-rs-fonts", "");
    f.href = "https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=Barlow+Condensed:ital,wght@0,700;0,800;1,700;1,800&family=Barlow:wght@500;600;700&display=swap";
    document.head.appendChild(f);
  }

  function bar() {
    if (document.querySelector(".rs-bar")) return;
    var el = document.createElement("div");
    el.className = "rs-bar";
    el.innerHTML =
      '<a class="rs-bar__brand" href="' + HOME + '">RAM<i>/</i>SHIRI</a>' +
      '<a class="rs-bar__back" href="' + HOME + '#builds"><span aria-hidden="true">&larr;</span> All projects</a>' +
      '<button class="rs-bar__style" type="button" aria-label="Switch design"><b>C</b><span aria-hidden="true">/</span><b>A</b></button>';
    document.body.insertBefore(el, document.body.firstChild);
    el.querySelector(".rs-bar__style").addEventListener("click", function () {
      var next = root.getAttribute("data-site-style") === "a" ? "c" : "a";
      try { localStorage.setItem(KEY, next); } catch (e) {}
      apply(next);
      window.dispatchEvent(new CustomEvent("sitestylechange", { detail: next }));
    });
    apply(root.getAttribute("data-site-style"));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bar); else bar();
})();
