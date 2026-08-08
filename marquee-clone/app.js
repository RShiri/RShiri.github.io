/* ===========================================================================
   Touchline app — UI wiring. Routes parsed intents to renderers and keeps
   every score expandable to its reasoning.
   =========================================================================== */
"use strict";
(function () {
  const TL = window.TL, E = TL.engine;
  const $ = (s) => document.querySelector(s);
  const feed = $("#feed");

  const EXAMPLES = [
    "Find a tall, fast striker with good ball control",
    "Young left-footed winger under €15m",
    "Pressing central midfielder under 23",
    "Ball-playing centre-back, good in the air",
    "What's on the market right now?",
    "Where is my squad weakest?"
  ];

  /* ---- sidebar ---- */
  function renderLegend() {
    const el = $("#model-legend");
    el.innerHTML = Object.values(E.MODELS).map(m =>
      `<div class="row"><b>${m.label}</b><span>${m.desc}</span></div>`).join("");
  }
  $("#dna-style").addEventListener("change", (e) => {
    TL.club.style = e.target.value;
    note(`Game model set to <b>${e.target.options[e.target.selectedIndex].text}</b>. Tactical-fit and overall scores now weigh ${e.target.value === "possession" ? "passing, control and composure" : e.target.value === "transition" ? "pace, dribbling and finishing" : "pressing, stamina and pace"}. Re-run a query to see the ranking move.`);
  });
  $("#dna-budget").addEventListener("input", (e) => {
    TL.club.budgetM = +e.target.value;
    $("#dna-budget-out").textContent = `€${e.target.value}m`;
  });

  /* ---- chips ---- */
  const chips = $("#chips");
  chips.innerHTML = EXAMPLES.map(x => `<button class="chip">${x}</button>`).join("");
  chips.addEventListener("click", (e) => {
    if (e.target.classList.contains("chip")) { $("#q").value = e.target.textContent; ask(); }
  });

  /* ---- ask flow ---- */
  $("#go").addEventListener("click", ask);
  $("#q").addEventListener("keydown", (e) => { if (e.key === "Enter") ask(); });

  function ask() {
    const text = $("#q").value.trim();
    if (!text) return;
    const intent = E.parseQuery(text);
    const turn = document.createElement("div");
    turn.innerHTML = `<div class="turn-q">${esc(text)}</div>`;
    const a = document.createElement("div");
    a.className = "turn-a";
    turn.appendChild(a);
    feed.prepend(turn);
    render(intent, a);
    $("#q").value = "";
  }

  function note(html) {
    const d = document.createElement("div");
    d.innerHTML = `<p class="answer-note">${html}</p>`;
    feed.prepend(d);
  }

  function render(intent, a) {
    switch (intent.type) {
      case "report": return renderReport(E.evaluate(intent.anchor, { club: TL.club }), a);
      case "similar": return renderSimilar(intent.anchor, a);
      case "market": return renderMarket(a);
      case "squad": return renderSquad(a);
      case "compare": return renderCompare(intent.pair, a);
      default: return renderShortlist(intent.filters, a);
    }
  }

  /* ---- renderers ---- */

  function renderShortlist(filters, a) {
    const { results, poolSize, relaxed } = E.shortlist(filters);
    if (!results.length) {
      a.innerHTML = `<p class="answer-note">No player in the database clears those constraints. Loosen the budget, age or trait thresholds and try again.</p>`;
      return;
    }
    const understood = filters.notes.length ? `Parsed: <b>${filters.notes.map(esc).join("</b> · <b>")}</b>` : "No hard constraints parsed — ranking the whole pool";
    const relaxNote = relaxed ? ` <span class="small">(no exact match — ${relaxed}; nearest profiles shown)</span>` : "";
    a.innerHTML = `<p class="answer-note">${understood}${filters.maxAge ? ` · age ≤ ${filters.maxAge}` : ""}${filters.maxValue ? ` · value ≤ €${filters.maxValue}m` : ""} — ${poolSize} candidates matched, top ${results.length} ranked against ${esc(TL.club.name)}'s ${TL.club.style} profile (budget €${TL.club.budgetM}m).${relaxNote}</p>`
      + results.map(ev => cardHTML(ev)).join("");
    wireCards(a);
  }

  function renderSimilar(anchor, a) {
    const sims = E.similarTo(anchor);
    a.innerHTML = `<p class="answer-note">Nearest neighbours to <b>${esc(anchor.name)}</b> (${anchor.posLabel}, ${esc(anchor.club)}) by cosine similarity over the 13-attribute vector:</p>`
      + sims.map(ev => cardHTML(ev, `similarity ${ev.similarity}%`)).join("");
    wireCards(a);
  }

  function renderReport(ev, a) {
    const paras = E.writeReport(ev);
    a.innerHTML = `<div class="report">` +
      paras.map((p, i) => `<p class="${i === paras.length - 1 ? "verdict" : ""}">${esc(p)}</p>`).join("") +
      `</div>` + cardHTML(ev);
    wireCards(a);
  }

  function renderCompare(pair, a) {
    const evs = pair.map(p => E.evaluate(p, { club: TL.club }));
    a.innerHTML = `<p class="answer-note">Head-to-head against ${esc(TL.club.name)}'s profile — expand any bar for the reasoning.</p>`
      + evs.map(ev => cardHTML(ev)).join("");
    wireCards(a);
  }

  function renderMarket(a) {
    const items = E.marketWatch();
    a.innerHTML = `<p class="answer-note">Market watch — the availability, market and potential models scan all 120 profiles continuously for windows of opportunity:</p>`
      + items.map(it => `<div class="sig"><span class="tag tag--${it.kind.split(" ")[0]}">${it.kind}</span><span>${esc(it.text)} <span class="small">(fit vs. us: ${it.score}/100)</span></span></div>`).join("");
  }

  function renderSquad(a) {
    const rows = E.squadAnalysis();
    a.innerHTML = `<p class="answer-note">Squad audit for ${esc(TL.club.name)} — quality is the line's average model rating, flags feed the recruitment priorities:</p>
      <table class="sq"><tr><th>Line</th><th>Players</th><th>Quality</th><th>Avg age</th><th>Verdict</th></tr>` +
      rows.map(r => {
        const cls = /priority/.test(r.flag) ? "flag-bad" : /ageing/.test(r.flag) ? "flag-warn" : "flag-ok";
        return `<tr><td>${r.line}</td><td>${r.count}</td><td>${r.quality}/100</td><td>${r.age}</td><td class="${cls}">${r.flag}</td></tr>`;
      }).join("") + `</table>
      <p class="answer-note">Ask e.g. “find a ${rows.find(r => /priority|ageing/.test(r.flag))?.line === "ATT" ? "striker" : "centre-back"} under €${TL.club.budgetM}m” to act on a flag.</p>`;
  }

  /* ---- player card with per-model bars ---- */
  function cardHTML(ev, extraMeta) {
    const p = ev.player;
    const cls = ev.overall >= 75 ? "s-hi" : ev.overall >= 60 ? "s-md" : "s-lo";
    const bars = E.SCORING.map(k => {
      const part = ev.parts[k];
      const bcls = part.score >= 70 ? "" : part.score >= 50 ? "mid" : "low";
      return `<div class="bar ${bcls}" data-model="${k}" data-pid="${p.id}" title="Click for reasoning">
        <div class="lbl"><span>${E.MODELS[k].label}</span><span>${part.score}</span></div>
        <div class="track"><div class="fill" style="width:${part.score}%"></div></div>
      </div>`;
    }).join("");
    return `<div class="pcard" data-pid="${p.id}">
      <div class="pcard-top">
        <div><span class="nm">${esc(p.name)}</span>
          <div class="meta">${p.posLabel} · ${p.age}y · ${p.height}cm · ${p.foot}-footed · ${esc(p.club)} (${esc(p.league)}) · €${p.value}m · contract ${p.contractUntil}${extraMeta ? " · " + extraMeta : ""}</div>
        </div>
        <div class="ovr ${cls}">${ev.overall}</div>
      </div>
      <div class="bars">${bars}<div class="why" data-why="${p.id}"></div></div>
      <div class="actions">
        <button class="btn btn--ghost btn--sm" data-act="report" data-pid="${p.id}">360° report</button>
        <button class="btn btn--ghost btn--sm" data-act="similar" data-pid="${p.id}">Find similar</button>
      </div>
    </div>`;
  }

  function wireCards(scope) {
    scope.addEventListener("click", (e) => {
      const bar = e.target.closest(".bar");
      if (bar) {
        const p = findAny(+bar.dataset.pid);
        const ev = E.evaluate(p, { club: TL.club });
        const part = ev.parts[bar.dataset.model];
        const why = bar.closest(".bars").querySelector(".why");
        why.classList.add("open");
        why.innerHTML = `<b>${E.MODELS[bar.dataset.model].label} → ${part.score}/100.</b> ${part.why.map(esc).join(" · ")}`;
        return;
      }
      const btn = e.target.closest("[data-act]");
      if (btn) {
        const p = findAny(+btn.dataset.pid);
        $("#q").value = btn.dataset.act === "report" ? `scout report on ${p.name}` : `find players similar to ${p.name}`;
        ask();
      }
    });
  }

  function findAny(id) { return TL.players.find(p => p.id === id) || TL.club.squad.find(p => p.id === id); }
  function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  renderLegend();
})();
