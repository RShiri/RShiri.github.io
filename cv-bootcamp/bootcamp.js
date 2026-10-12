/* CV bootcamp - one-page app. Content files push topic objects into
   window.BOOTCAMP_TOPICS; this file renders the dashboard (#) and topic pages (#t/<id>),
   runs the quizzes and keeps per-topic state in localStorage under "cvboot:<id>".
   Topic shape: { id, group, title, cv:[CV tokens], summary, usedIn:[project ids], risk?,
   dropAdvice?, html, tip, questions:[{q, code?, choices, answer, explain}], open:[{q, a}] }.
   Strings are authored HTML (static content in this repo), so they go in via innerHTML. */
(function () {
  "use strict";

  var KEEP_AT = 70;   // best score that recommends keeping a skill
  var WEAK_AT = 50;   // below this the recommendation is to remove it

  var GROUPS = [
    { id: "lang", name: "שפות תכנות", cvLabel: "Languages" },
    { id: "dataml", name: "דאטה ולמידת מכונה", cvLabel: "Data & ML" },
    { id: "de", name: "הנדסת נתונים", cvLabel: "Data Engineering" },
    { id: "ai", name: "פיתוח בעזרת AI", cvLabel: "AI-Assisted Development" },
    { id: "proj", name: "טענות מתוך הפרויקטים", cvLabel: null },
    { id: "target", name: "הכנה לחברות היעד", cvLabel: null, prep: true }
  ];
  var PROJECTS = {
    laliga: "La Liga Match Data Pipeline",
    worldcup: "World Cup Analysis Pipeline",
    barca: "Barcelona Elite Analyzer",
    xepl: "EPL Analytics (XEPL)"
  };

  var TOPICS = window.BOOTCAMP_TOPICS || [];
  var byId = {};
  TOPICS.forEach(function (t) { byId[t.id] = t; });
  // dashboard / pager order follows GROUPS order, then file order
  var ORDER = [];
  GROUPS.forEach(function (g) { TOPICS.forEach(function (t) { if (t.group === g.id) ORDER.push(t); }); });

  var app = document.getElementById("app");
  var TARGETS = window.BOOTCAMP_TARGETS || null;

  // prep topics (group.prep) are interview material for target companies, not CV claims:
  // they get a readiness verdict instead of keep/drop and stay out of the CV counts
  function isPrep(t) { return GROUPS.some(function (g) { return g.id === t.group && g.prep; }); }

  /* ---------- storage (best-effort: page works without it) ---------- */
  function load(id) {
    try {
      var raw = localStorage.getItem("cvboot:" + id);
      if (raw) return JSON.parse(raw);
    } catch (e) {}
    return { best: null, last: null, verdict: null };
  }
  function save(id, st) {
    try { localStorage.setItem("cvboot:" + id, JSON.stringify(st)); } catch (e) {}
  }

  function recommendation(st) {
    if (st.best === null || st.best === undefined) return null;
    if (st.best >= KEEP_AT) return "keep";
    if (st.best >= WEAK_AT) return "weak";
    return "drop";
  }

  /* ---------- theme toggle ---------- */
  var toggle = document.getElementById("themeToggle");
  function applyTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    if (toggle) toggle.textContent = t === "dark" ? "☀️" : "🌙";
  }
  applyTheme(document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark");
  if (toggle) toggle.addEventListener("click", function () {
    var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    try { localStorage.setItem("theme", next); } catch (e) {}
    applyTheme(next);
  });

  /* ---------- tiny DOM helpers ---------- */
  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html !== undefined) n.innerHTML = html;
    return n;
  }
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }
  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  function statusPill(st, prep) {
    if (prep) {
      var r = recommendation(st);
      if (r === "keep") return '<span class="pill pill--keep">מוכן</span>';
      if (r === "weak") return '<span class="pill pill--weak">צריך חיזוק</span>';
      if (r === "drop") return '<span class="pill pill--drop">לא מוכן</span>';
      return '<span class="pill">עוד לא נבחן</span>';
    }
    if (st.verdict === "keep") return '<span class="pill pill--keep">נשאר בקו״ח</span>';
    if (st.verdict === "drop") return '<span class="pill pill--drop">יורד מהקו״ח</span>';
    var rec = recommendation(st);
    if (rec === "keep") return '<span class="pill pill--keep">עבר, ממתין להחלטה</span>';
    if (rec === "weak") return '<span class="pill pill--weak">צריך חיזוק</span>';
    if (rec === "drop") return '<span class="pill pill--drop">נכשל, ממתין להחלטה</span>';
    return '<span class="pill">עוד לא נבחן</span>';
  }

  /* ======================================================================
     Dashboard
     ====================================================================== */
  function renderDashboard() {
    document.title = "בוטקאמפ קורות חיים";
    app.textContent = "";

    var states = {};
    var tested = 0, kept = 0, dropped = 0, pending = 0;
    var cvTopics = ORDER.filter(function (t) { return !isPrep(t); });
    ORDER.forEach(function (t) { states[t.id] = load(t.id); });
    cvTopics.forEach(function (t) {
      var st = states[t.id];
      if (st.best !== null && st.best !== undefined) tested++;
      if (st.verdict === "keep") kept++;
      else if (st.verdict === "drop") dropped++;
      else pending++;
    });

    var head = el("div", "page-head",
      '<span class="kicker">כל מה שכתבת בקורות החיים, נבדק אחד־אחד</span>' +
      '<h1>בוטקאמפ <span class="grad">קורות חיים</span></h1>' +
      '<p class="lead">לכל מיומנות שמופיעה בקו״ח יש כאן דף: הסבר ממוקד לראיון, מבחן אינטראקטיבי ושאלות ראיון פתוחות. ' +
      'בסוף כל דף מחליטים: <strong>נשאר</strong> או <strong>יורד מהקו״ח</strong>. ' +
      'למטה בדף הזה נבנית אוטומטית שורת ה־Skills המעודכנת להעתקה.</p>');
    app.appendChild(head);

    app.appendChild(el("ol", "steps",
      "<li>קוראים את ההסבר. אם משהו לא מוכר בכלל, זה סימן ראשון.</li>" +
      "<li>עונים על המבחן. מעל " + KEEP_AT + "% ההמלצה היא להשאיר, ומתחת ל־" + WEAK_AT + "% להוריד.</li>" +
      "<li>מחליטים בכפתור בתחתית הדף, ומעתיקים את שורת הכישורים החדשה.</li>"));

    app.appendChild(el("div", "stats",
      '<div class="stat"><div class="n">' + tested + "/" + cvTopics.length + '</div><div class="l">נושאים שנבחנו</div></div>' +
      '<div class="stat stat--ok"><div class="n">' + kept + '</div><div class="l">נשארים</div></div>' +
      '<div class="stat stat--bad"><div class="n">' + dropped + '</div><div class="l">יורדים</div></div>' +
      '<div class="stat stat--warn"><div class="n">' + pending + '</div><div class="l">ממתינים להחלטה</div></div>'));

    if (TARGETS) {
      var feat = el("a", "card card--feature");
      feat.href = "#targets";
      feat.innerHTML = '<div class="card-top"><h3>תוכנית הפעולה: Marquee ו־LSports</h3><span class="pill pill--keep">חדש</span></div>' +
        "<p>מה כל חברה עושה, למה אתה מתאים, מה חסר, הודעות מוכנות לשליחה, ורשימת צעדים לסמן.</p>" +
        '<div class="card-foot"><span>צעדים שבוצעו</span><b>' + doneCount() + "/" + TARGETS.steps.length + "</b></div>";
      app.appendChild(feat);
    }

    GROUPS.forEach(function (g) {
      var topics = ORDER.filter(function (t) { return t.group === g.id; });
      if (!topics.length) return;
      var sec = el("section", "group");
      var cvline = g.cvLabel
        ? '<span class="cvline">בקו״ח תחת השורה ' + "<bdi>" + esc(g.cvLabel) + "</bdi></span>"
        : g.prep ? '<span class="cvline">לא בקו״ח, אבל ישאלו עליהם</span>'
        : '<span class="cvline">משפטים מתוך תיאורי הפרויקטים</span>';
      sec.appendChild(el("div", "group-head", "<h2>" + g.name + "</h2>" + cvline));
      var cards = el("div", "cards");
      topics.forEach(function (t) {
        var st = states[t.id];
        var a = el("a", "card" + (st.verdict === "drop" ? " is-drop" : ""));
        a.href = "#t/" + t.id;
        var score = st.best === null || st.best === undefined ? "—" : st.best + "%";
        a.innerHTML =
          '<div class="card-top"><h3><bdi>' + esc(t.title) + "</bdi></h3>" + statusPill(st, isPrep(t)) + "</div>" +
          "<p>" + t.summary + "</p>" +
          (t.risk ? '<span class="pill pill--risk">' + (t.riskPill || "אין פרויקט שמגבה") + "</span>" : "") +
          '<div class="card-foot"><span>ציון הכי טוב</span><b>' + score + "</b></div>";
        cards.appendChild(a);
      });
      sec.appendChild(cards);
      app.appendChild(sec);
    });

    app.appendChild(renderCvOutput(states));
  }

  /* ---------- generated CV skills block ---------- */
  function renderCvOutput(states) {
    var box = el("section", "cv-out");
    box.appendChild(el("h2", null, "שורת הכישורים המעודכנת"));
    box.appendChild(el("p", null,
      "כל מה שלא סימנת כ״יורד״ נשאר בשורה. אפשר להעתיק ישר לקו״ח."));

    var lines = [];
    GROUPS.forEach(function (g) {
      if (!g.cvLabel) return;
      var tokens = [];
      ORDER.forEach(function (t) {
        if (t.group === g.id && states[t.id].verdict !== "drop") tokens = tokens.concat(t.cv);
      });
      if (tokens.length) lines.push(g.cvLabel + ": " + tokens.join(", "));
    });
    lines.push("Spoken Languages: Hebrew (native), English (proficient)");
    var text = lines.join("\n");

    var pre = el("pre", "cv-text");
    pre.textContent = text;
    box.appendChild(pre);

    var actions = el("div", "quiz-actions");
    var copy = el("button", "btn btn--primary", "העתקה ללוח");
    copy.type = "button";
    copy.addEventListener("click", function () {
      function done() { copy.textContent = "הועתק ✓"; setTimeout(function () { copy.textContent = "העתקה ללוח"; }, 1800); }
      try {
        navigator.clipboard.writeText(text).then(done, function () { selectPre(pre); });
      } catch (e) { selectPre(pre); }
    });
    actions.appendChild(copy);
    var reset = el("button", "btn btn--ghost", "איפוס כל ההתקדמות");
    reset.type = "button";
    reset.addEventListener("click", function () {
      if (!window.confirm("למחוק את כל הציונים וההחלטות?")) return;
      ORDER.forEach(function (t) { try { localStorage.removeItem("cvboot:" + t.id); } catch (e) {} });
      renderDashboard();
    });
    actions.appendChild(reset);
    box.appendChild(actions);

    // what was dropped, and which project bullets now lean on a dropped skill
    var dropped = ORDER.filter(function (t) { return states[t.id].verdict === "drop"; });
    if (dropped.length) {
      box.appendChild(el("h3", null, "מה ירד"));
      var ul = el("ul");
      dropped.forEach(function (t) {
        var li = el("li", null, "<bdi>" + esc(t.title) + "</bdi>" + (t.dropAdvice ? ". " + t.dropAdvice : "."));
        ul.appendChild(li);
      });
      box.appendChild(ul);

      var warnings = [];
      Object.keys(PROJECTS).forEach(function (pid) {
        var hits = dropped.filter(function (t) { return (t.usedIn || []).indexOf(pid) !== -1; });
        if (hits.length) {
          warnings.push("<li>הפרויקט <bdi>" + esc(PROJECTS[pid]) + "</bdi> נשען על " +
            hits.map(function (t) { return "<bdi>" + esc(t.title) + "</bdi>"; }).join(" ו־") +
            ". בראיון ישאלו עליו, אז או שתלמד את הנושא, או שתנסח מחדש את תיאור הפרויקט.</li>");
        }
      });
      if (warnings.length) {
        box.appendChild(el("h3", null, "שים לב לפרויקטים"));
        box.appendChild(el("ul", null, warnings.join("")));
      }
    }
    return box;
  }
  function selectPre(pre) {
    var r = document.createRange();
    r.selectNodeContents(pre);
    var s = window.getSelection();
    s.removeAllRanges();
    s.addRange(r);
  }

  /* ======================================================================
     Topic page
     ====================================================================== */
  function renderTopic(t) {
    document.title = t.title + " · בוטקאמפ קורות חיים";
    app.textContent = "";
    var group = GROUPS.filter(function (g) { return g.id === t.group; })[0];
    var pos = ORDER.indexOf(t);

    app.appendChild(el("div", "page-head",
      '<span class="kicker">נושא ' + (pos + 1) + " מתוך " + ORDER.length + " · " + group.name + "</span>" +
      '<h1><bdi>' + esc(t.title) + "</bdi></h1>" +
      '<p class="lead">' + t.summary + "</p>"));

    var cvBox = group.prep
      ? '<span class="box-title">למה זה חשוב</span>' + t.why
      : '<span class="box-title">מה כתוב עליך בקו״ח</span>' +
      (group.cvLabel
        ? "בשורת הכישורים <bdi>" + esc(group.cvLabel) + "</bdi> מופיע: <bdi>" + esc(t.cv.join(", ")) + "</bdi>."
        : "התיאור של הפרויקט טוען לזה במפורש.");
    if (!group.prep && t.usedIn && t.usedIn.length) {
      cvBox += "<br>מופיע בפרויקטים: " + t.usedIn.map(function (p) { return "<bdi>" + esc(PROJECTS[p]) + "</bdi>"; }).join(", ") + ".";
    }
    app.appendChild(el("div", "box box--cv", cvBox));
    if (t.risk) app.appendChild(el("div", "box box--risk", '<span class="box-title">סיכון</span>' + t.risk));

    app.appendChild(el("article", "study", t.html));
    if (t.tip) app.appendChild(el("div", "box box--tip", '<span class="box-title">איך לענות בראיון</span>' + t.tip));

    var quizRoot = el("div", "quiz");
    app.appendChild(quizRoot);

    if (t.open && t.open.length) {
      var oq = el("section", "open-qs");
      oq.appendChild(el("h2", null, "שאלות ראיון פתוחות"));
      oq.appendChild(el("p", null, "נסה לענות בקול לפני שאתה פותח את התשובה."));
      t.open.forEach(function (o) {
        var d = el("details", "oq");
        d.appendChild(el("summary", null, o.q));
        d.appendChild(el("div", "oq-body", o.a));
        oq.appendChild(d);
      });
      app.appendChild(oq);
    }

    var verdictRoot = el("section", "verdict-panel");
    app.appendChild(verdictRoot);
    renderVerdict(t, verdictRoot);

    var pager = el("nav", "pager");
    var prev = ORDER[pos - 1], next = ORDER[pos + 1];
    pager.appendChild(prev
      ? el("a", "btn btn--ghost", "→ <bdi>" + esc(prev.title) + "</bdi>")
      : el("a", "btn btn--ghost", "→ ללוח הבקרה"));
    pager.lastChild.href = prev ? "#t/" + prev.id : "#";
    pager.appendChild(next
      ? el("a", "btn btn--ghost", "<bdi>" + esc(next.title) + "</bdi> ←")
      : el("a", "btn btn--ghost", "ללוח הבקרה ←"));
    pager.lastChild.href = next ? "#t/" + next.id : "#";
    app.appendChild(pager);

    runQuiz(t, quizRoot, function () { renderVerdict(t, verdictRoot); });
    window.scrollTo(0, 0);
  }

  function renderVerdict(t, root) {
    var st = load(t.id);
    var rec = recommendation(st);
    if (isPrep(t)) {
      root.className = "verdict-panel" + (rec === "keep" ? " is-keep" : rec === "drop" ? " is-drop" : "");
      root.innerHTML = "<h2>מוכן לשאלות על זה?</h2><p>" +
        (rec === null ? "עוד לא עשית את המבחן."
          : rec === "keep" ? "הציון הכי טוב שלך הוא " + st.best + "%. מוכן. לפני הראיון תעבור שוב על השאלות הפתוחות."
          : "הציון הכי טוב שלך הוא " + st.best + "%. עוד לא שם. תקרא שוב את ההסבר ותיבחן מחדש.") +
        "</p>";
      var back = el("a", "btn btn--ghost", "לתוכנית הפעולה");
      back.href = "#targets";
      var row = el("div", "quiz-actions");
      row.appendChild(back);
      root.appendChild(row);
      return;
    }
    root.className = "verdict-panel" + (st.verdict === "keep" ? " is-keep" : st.verdict === "drop" ? " is-drop" : "");
    var msg;
    if (rec === null) msg = "עוד לא עשית את המבחן. אפשר להחליט גם בלעדיו, אבל עדיף לבדוק את עצמך קודם.";
    else if (rec === "keep") msg = "הציון הכי טוב שלך הוא " + st.best + "%. ההמלצה: להשאיר בקו״ח, ולעבור על השאלות הפתוחות לפני ראיון.";
    else if (rec === "weak") msg = "הציון הכי טוב שלך הוא " + st.best + "%. זה גבולי. או שתחזור על ההסבר ותיבחן שוב, או שתוריד.";
    else msg = "הציון הכי טוב שלך הוא " + st.best + "%. ההמלצה: להוריד מהקו״ח, אלא אם אתה מתכוון ללמוד את זה לפני הראיון.";

    var now = st.verdict === "keep" ? "<p><strong>ההחלטה הנוכחית: נשאר בקו״ח.</strong></p>"
      : st.verdict === "drop" ? "<p><strong>ההחלטה הנוכחית: יורד מהקו״ח.</strong></p>" : "";
    root.innerHTML = "<h2>אז זה נשאר בקורות החיים?</h2><p>" + msg + "</p>" + now;

    var actions = el("div", "quiz-actions");
    var keep = el("button", "btn btn--keep" + (st.verdict === "keep" ? " is-on" : ""), "אני יודע את זה, להשאיר");
    var drop = el("button", "btn btn--drop" + (st.verdict === "drop" ? " is-on" : ""), "לא יודע, להוריד מהקו״ח");
    keep.type = drop.type = "button";
    keep.addEventListener("click", function () { setVerdict(t, "keep", root); });
    drop.addEventListener("click", function () { setVerdict(t, "drop", root); });
    actions.appendChild(keep);
    actions.appendChild(drop);
    if (st.verdict) {
      var clear = el("button", "btn btn--ghost btn--sm", "ביטול החלטה");
      clear.type = "button";
      clear.addEventListener("click", function () { setVerdict(t, null, root); });
      actions.appendChild(clear);
    }
    root.appendChild(actions);
  }
  function setVerdict(t, v, root) {
    var st = load(t.id);
    st.verdict = v;
    save(t.id, st);
    renderVerdict(t, root);
  }

  /* ---------- quiz engine ---------- */
  function runQuiz(t, root, onFinish) {
    var questions = shuffle(t.questions);
    var idx = 0, score = 0;

    function renderQuestion() {
      root.textContent = "";
      var q = questions[idx];
      var head = el("div", "quiz-head");
      head.appendChild(el("h2", null, "מבחן ידע"));
      head.appendChild(el("span", "quiz-progress", "שאלה " + (idx + 1) + " מתוך " + questions.length + " · " + score + " נכונות"));
      root.appendChild(head);
      root.appendChild(el("p", "quiz-q", q.q));
      if (q.code) {
        var pre = el("pre");
        var code = el("code");
        code.textContent = q.code;
        pre.appendChild(code);
        root.appendChild(pre);
      }
      var order = shuffle(q.choices.map(function (_, i) { return i; }));
      var list = el("ul", "quiz-choices");
      order.forEach(function (ci) {
        var li = el("li");
        var btn = el("button", null, q.choices[ci]);
        btn.type = "button";
        btn.dir = "auto";
        btn.setAttribute("data-ci", ci);
        btn.addEventListener("click", function () { pick(ci, list); });
        li.appendChild(btn);
        list.appendChild(li);
      });
      root.appendChild(list);
    }

    function pick(ci, list) {
      var q = questions[idx];
      if (list.getAttribute("data-done")) return;
      list.setAttribute("data-done", "1");
      var good = ci === q.answer;
      if (good) score++;
      list.querySelectorAll("button").forEach(function (b) {
        var bi = parseInt(b.getAttribute("data-ci"), 10);
        b.disabled = true;
        if (bi === q.answer) b.classList.add("correct");
        else if (bi === ci) b.classList.add("wrong");
      });
      root.appendChild(el("div", "quiz-explain " + (good ? "good" : "bad"),
        "<b>" + (good ? "נכון. " : "לא בדיוק. ") + "</b>" + q.explain));
      var actions = el("div", "quiz-actions");
      var last = idx === questions.length - 1;
      var next = el("button", "btn btn--primary", last ? "לציון שלי" : "לשאלה הבאה");
      next.type = "button";
      next.addEventListener("click", function () {
        if (last) renderResult(); else { idx++; renderQuestion(); }
      });
      actions.appendChild(next);
      root.appendChild(actions);
      next.focus({ preventScroll: true });
    }

    function renderResult() {
      var pct = Math.round((score / questions.length) * 100);
      var st = load(t.id);
      st.last = pct;
      if (st.best === null || st.best === undefined || pct > st.best) st.best = pct;
      save(t.id, st);

      root.textContent = "";
      var res = el("div", "quiz-result");
      res.appendChild(el("div", "big", pct + "%"));
      var verdict = pct >= KEEP_AT ? "מוכן לראיון בנושא הזה"
        : pct >= WEAK_AT ? "גבולי. כדאי לחזור על ההסבר ולנסות שוב"
        : "הנושא לא יושב. ההמלצה היא להוריד אותו או ללמוד ברצינות";
      var v = el("div", "verdict", verdict);
      v.style.color = pct >= KEEP_AT ? "var(--ok)" : pct >= WEAK_AT ? "var(--warn)" : "var(--bad)";
      res.appendChild(v);
      res.appendChild(el("div", "sub", score + " מתוך " + questions.length + " נכונות · הציון הכי טוב: " + st.best + "%"));
      var actions = el("div", "quiz-actions");
      var retry = el("button", "btn btn--primary", "למבחן שוב (בסדר אחר)");
      retry.type = "button";
      retry.addEventListener("click", function () { questions = shuffle(t.questions); idx = 0; score = 0; renderQuestion(); });
      actions.appendChild(retry);
      res.appendChild(actions);
      root.appendChild(res);
      onFinish();
    }

    renderQuestion();
  }

  /* ======================================================================
     Targets page (#targets): company dossiers, action checklist, outreach templates.
     Data comes from window.BOOTCAMP_TARGETS = { companies, steps, templates, sources }.
     ====================================================================== */
  function stepKey(id) { return "cvboot:step:" + id; }
  function stepDone(id) {
    try { return localStorage.getItem(stepKey(id)) === "1"; } catch (e) { return false; }
  }
  function doneCount() {
    return TARGETS ? TARGETS.steps.filter(function (s) { return stepDone(s.id); }).length : 0;
  }

  function copyButton(text, label) {
    var btn = el("button", "btn btn--ghost btn--sm", label || "העתקה");
    btn.type = "button";
    btn.addEventListener("click", function () {
      var orig = btn.textContent;
      function done() { btn.textContent = "הועתק ✓"; setTimeout(function () { btn.textContent = orig; }, 1800); }
      try { navigator.clipboard.writeText(text).then(done, function () {}); } catch (e) {}
    });
    return btn;
  }

  function renderTargets() {
    document.title = "תוכנית פעולה · בוטקאמפ קורות חיים";
    app.textContent = "";
    app.appendChild(el("div", "page-head",
      '<span class="kicker">מהבוטקאמפ לחוזה</span>' +
      "<h1>תוכנית הפעולה: <bdi>Marquee</bdi> ו־<bdi>LSports</bdi></h1>" +
      '<p class="lead">' + TARGETS.lead + "</p>"));

    TARGETS.companies.forEach(function (c) {
      var sec = el("section", "target");
      sec.appendChild(el("div", "group-head", "<h2><bdi>" + esc(c.name) + "</bdi></h2>" + '<span class="pill ' + c.pillClass + '">' + c.pill + "</span>"));
      sec.appendChild(el("p", "target-tag", c.tagline));
      var grid = el("div", "target-grid");
      grid.appendChild(el("div", "box", '<span class="box-title">מה ידוע עליהם</span><ul>' + c.facts.map(function (f) { return "<li>" + f + "</li>"; }).join("") + "</ul>"));
      grid.appendChild(el("div", "box box--tip", '<span class="box-title">למה אתה מתאים</span><ul>' + c.fit.map(function (f) { return "<li>" + f + "</li>"; }).join("") + "</ul>"));
      grid.appendChild(el("div", "box box--risk", '<span class="box-title">מה חסר, ואיפה סוגרים את זה</span><ul>' + c.gaps.map(function (f) { return "<li>" + f + "</li>"; }).join("") + "</ul>"));
      sec.appendChild(grid);
      app.appendChild(sec);
    });

    var steps = el("section", "target");
    steps.appendChild(el("div", "group-head", "<h2>הצעדים, לפי הסדר</h2><span class=\"cvline\">מסמנים כשביצעת. נשמר בדפדפן</span>"));
    var list = el("ol", "checklist");
    TARGETS.steps.forEach(function (st) {
      var li = el("li", stepDone(st.id) ? "is-done" : "");
      var label = el("label");
      var cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = stepDone(st.id);
      cb.addEventListener("change", function () {
        try { localStorage.setItem(stepKey(st.id), cb.checked ? "1" : "0"); } catch (e) {}
        li.className = cb.checked ? "is-done" : "";
      });
      label.appendChild(cb);
      label.appendChild(el("span", null, '<b class="step-for">' + st.who + "</b> " + st.text));
      li.appendChild(label);
      list.appendChild(li);
    });
    steps.appendChild(list);
    app.appendChild(steps);

    var tpl = el("section", "target");
    tpl.appendChild(el("div", "group-head", "<h2>הודעות מוכנות</h2><span class=\"cvline\">באנגלית, להעתקה. תעבור עליהן ותתאים לפני שליחה</span>"));
    TARGETS.templates.forEach(function (t) {
      var card = el("div", "tpl");
      var head = el("div", "tpl-head", "<h3>" + t.title + "</h3>");
      head.appendChild(copyButton(t.text));
      card.appendChild(head);
      if (t.note) card.appendChild(el("p", "tpl-note", t.note));
      var pre = el("pre", "cv-text");
      pre.textContent = t.text;
      card.appendChild(pre);
      tpl.appendChild(card);
    });
    app.appendChild(tpl);

    var src = el("section", "target");
    src.appendChild(el("h2", null, "מקורות"));
    src.appendChild(el("ul", "sources", TARGETS.sources.map(function (x) {
      return '<li><a href="' + esc(x.url) + '" target="_blank" rel="noopener"><bdi>' + esc(x.title) + "</bdi></a></li>";
    }).join("")));
    app.appendChild(src);

    var pager = el("nav", "pager");
    var back = el("a", "btn btn--ghost", "→ ללוח הבקרה");
    back.href = "#";
    pager.appendChild(back);
    app.appendChild(pager);
    window.scrollTo(0, 0);
  }

  /* ---------- router ---------- */
  function route() {
    var m = /^#t\/([\w-]+)$/.exec(location.hash);
    if (m && byId[m[1]]) renderTopic(byId[m[1]]);
    else if (location.hash === "#targets" && TARGETS) renderTargets();
    else renderDashboard();
  }
  window.addEventListener("hashchange", route);
  route();
})();
