/* LSports prep - shared page logic: theme toggle, quiz engine, dashboard scores.
   Quiz pages define window.QUIZ = { id, title, pass, questions:[{q, code?, choices, answer, explain}] }
   and include an empty <div id="quiz"></div>. Best scores persist in localStorage
   under "lsprep:<id>:best" so the dashboard can show progress. */
(function () {
  "use strict";

  /* ---------- theme toggle (same storage key as the main site) ---------- */
  var toggle = document.getElementById("themeToggle");
  function applyTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    if (toggle) {
      toggle.textContent = t === "dark" ? "☀️" : "🌙";
      toggle.setAttribute("aria-label", t === "dark" ? "Switch to light mode" : "Switch to dark mode");
    }
  }
  applyTheme(document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark");
  if (toggle) toggle.addEventListener("click", function () {
    var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    try { localStorage.setItem("theme", next); } catch (e) {}
    applyTheme(next);
  });

  function bestKey(id) { return "lsprep:" + id + ":best"; }
  function getBest(id) {
    try { var v = localStorage.getItem(bestKey(id)); return v === null ? null : parseInt(v, 10); }
    catch (e) { return null; }
  }
  function setBest(id, pct) {
    try {
      var prev = getBest(id);
      if (prev === null || pct > prev) localStorage.setItem(bestKey(id), String(pct));
    } catch (e) {}
  }

  /* ---------- dashboard: fill best scores into [data-score-for] ---------- */
  var slots = document.querySelectorAll("[data-score-for]");
  slots.forEach(function (el) {
    var id = el.getAttribute("data-score-for");
    var best = getBest(id);
    var b = el.querySelector("b");
    if (!b) return;
    if (best === null) { b.textContent = "not taken"; return; }
    b.textContent = "best " + best + "%";
    if (best >= 80) { b.classList.add("ready"); b.textContent += " ✓"; }
  });

  /* ---------- quiz engine ---------- */
  var quiz = window.QUIZ;
  var root = document.getElementById("quiz");
  if (!quiz || !root) return;

  var passPct = Math.round((quiz.pass || 0.8) * 100);
  var idx = 0, score = 0, answered = false;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function renderQuestion() {
    answered = false;
    root.textContent = "";
    var q = quiz.questions[idx];

    var head = el("div", "quiz-head");
    head.appendChild(el("h2", null, quiz.title || "Knowledge test"));
    head.appendChild(el("span", "quiz-progress", "Question " + (idx + 1) + " / " + quiz.questions.length + " · " + score + " correct"));
    root.appendChild(head);

    root.appendChild(el("p", "quiz-q", q.q));
    if (q.code) {
      var pre = el("pre", "quiz-code");
      pre.appendChild(el("code", null, q.code));
      root.appendChild(pre);
    }

    var list = el("ul", "quiz-choices");
    q.choices.forEach(function (choice, i) {
      var li = el("li");
      var btn = el("button", null, choice);
      btn.type = "button";
      btn.addEventListener("click", function () { pick(i, list); });
      li.appendChild(btn);
      list.appendChild(li);
    });
    root.appendChild(list);
  }

  function pick(i, list) {
    if (answered) return;
    answered = true;
    var q = quiz.questions[idx];
    var good = i === q.answer;
    if (good) score++;

    var buttons = list.querySelectorAll("button");
    buttons.forEach(function (b, j) {
      b.disabled = true;
      if (j === q.answer) b.classList.add("correct");
      else if (j === i) b.classList.add("wrong");
    });

    var ex = el("div", "quiz-explain " + (good ? "good" : "bad"));
    var lead = el("b", null, good ? "Correct. " : "Not quite. ");
    ex.appendChild(lead);
    ex.appendChild(document.createTextNode(q.explain));
    root.appendChild(ex);

    var actions = el("div", "quiz-actions");
    var last = idx === quiz.questions.length - 1;
    var next = el("button", "btn btn--primary", last ? "See my score" : "Next question →");
    next.type = "button";
    next.addEventListener("click", function () {
      if (last) renderResult(); else { idx++; renderQuestion(); }
    });
    actions.appendChild(next);
    root.appendChild(actions);
    next.focus();
  }

  function renderResult() {
    root.textContent = "";
    var pct = Math.round((score / quiz.questions.length) * 100);
    setBest(quiz.id, pct);
    var best = getBest(quiz.id);

    var res = el("div", "quiz-result");
    res.appendChild(el("div", "big", pct + "%"));
    var pass = pct >= passPct;
    res.appendChild(el("div", "verdict " + (pass ? "pass" : "fail"),
      pass ? "Interview ready ✓" : "Keep studying — pass bar is " + passPct + "%"));
    res.appendChild(el("div", "sub",
      score + " of " + quiz.questions.length + " correct" +
      (best !== null ? " · best so far: " + best + "%" : "")));

    var bar = el("div", "quiz-bar");
    var fill = el("i");
    bar.appendChild(fill);
    bar.appendChild(el("em"));
    res.appendChild(bar);

    var actions = el("div", "quiz-actions");
    actions.style.justifyContent = "center";
    var retry = el("button", "btn btn--primary", "Retake test");
    retry.type = "button";
    retry.addEventListener("click", function () { idx = 0; score = 0; renderQuestion(); });
    actions.appendChild(retry);
    var backLink = el("a", "btn btn--ghost", "← Back to dashboard");
    backLink.href = "../index.html";
    actions.appendChild(backLink);
    res.appendChild(actions);

    root.appendChild(res);
    requestAnimationFrame(function () { fill.style.width = pct + "%"; });
  }

  renderQuestion();
})();
