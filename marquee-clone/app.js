/* ===========================================================================
   Touchline app — UI wiring over the real player database.
   =========================================================================== */
"use strict";
(function () {
  const TL = window.TL;
  const $ = (s) => document.querySelector(s);
  let E, feed;

  const EXAMPLES = [
    "Find a tall, fast striker with good ball control",
    "Young left-footed winger with dribbling",
    "Pressing central midfielder under 23",
    "Ball-playing centre-back",
    "What's on the market right now?",
    "Where is my squad weakest?"
  ];

  /* ---------- boot ---------- */
  document.addEventListener("DOMContentLoaded", async () => {
    feed = $("#feed");
    try {
      await TL.load();
    } catch (err) {
      $("#boot").innerHTML = `<p class="answer-note">Could not load <code>players.json</code> — ${esc(err.message)}.
        Serve this folder over HTTP (<code>python3 -m http.server</code>) rather than opening the file directly.</p>`;
      return;
    }
    E = TL.engine;
    renderLegend();
    renderClubPicker();
    renderChips();
    const m = TL.meta;
    $("#boot").innerHTML = `<p class="answer-note">
      <b>${m.n_players.toLocaleString()} real players</b> across ${TL.leagues.length} competitions.
      ${m.n_verified.toLocaleString()} carry ratings derived from real ${m.seasons[0]}–${m.generated_for_season}
      match data; ${m.n_prior_only.toLocaleString()} sit on an EA FC 24 baseline because their league has no
      public event data. Ask anything above, or click an example.</p>`;
    wireCards(feed);
  });

  /* ---------- sidebar ---------- */
  function renderLegend() {
    $("#model-legend").innerHTML = Object.values(E.MODELS)
      .map(m => `<div class="row"><b>${m.label}</b><span>${m.desc}</span></div>`).join("");
  }

  function renderClubPicker() {
    const sel = $("#dna-club");
    sel.innerHTML = TL.clubs.map(c => `<option${c === TL.club.name ? " selected" : ""}>${esc(c)}</option>`).join("");
    sel.disabled = false;
    sel.addEventListener("change", () => {
      TL.setClub(sel.value);
      showSquadSummary();
      note(`Club set to <b>${esc(TL.club.name)}</b> (${esc(TL.club.league)}) — ${TL.club.squad.length} players in the database. Synergy and squad audits now run against this squad.`);
    });
    $("#dna-style").addEventListener("change", (e) => {
      TL.club.style = e.target.value;
      note(`Game model set to <b>${esc(e.target.options[e.target.selectedIndex].text)}</b>. Tactical fit now weighs ${e.target.value === "possession" ? "passing, control and composure" : e.target.value === "transition" ? "pace, dribbling and finishing" : "pressing, stamina and pace"}. Re-run a query to see the ranking move.`);
    });
    $("#dna-verified").addEventListener("change", (e) => {
      TL.club.verifiedOnly = e.target.checked;
      note(e.target.checked
        ? "Restricted to <b>verified</b> players only — those with a full season of real Big-5 match data behind their ratings."
        : "Showing all players, including those on an EA FC 24 baseline.");
    });
    showSquadSummary();
  }

  function showSquadSummary() {
    const s = TL.club.squad;
    const v = s.filter(p => p.conf === 2).length;
    $("#club-sub").innerHTML = `${esc(TL.club.league)} · ${s.length} players · ${v} verified`;
  }

  function renderChips() {
    const chips = $("#chips");
    chips.innerHTML = EXAMPLES.map(x => `<button class="chip">${x}</button>`).join("");
    chips.addEventListener("click", (e) => {
      if (e.target.classList.contains("chip")) { $("#q").value = e.target.textContent; ask(); }
    });
  }

  /* ---------- ask ---------- */
  $("#go").addEventListener("click", () => ask());
  $("#q").addEventListener("keydown", (e) => { if (e.key === "Enter") ask(); });

  function ask() {
    if (!E) return;
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

  /* ---------- renderers ---------- */
  function renderShortlist(filters, a) {
    const { results, poolSize, relaxed } = E.shortlist(filters);
    if (!results.length) {
      a.innerHTML = `<p class="answer-note">Nothing in the database clears those constraints. Try loosening the age, position or attribute thresholds.</p>`;
      return;
    }
    const parsed = filters.notes.length
      ? `Parsed: <b>${filters.notes.map(esc).join("</b> · <b>")}</b>`
      : "No hard constraints parsed — ranking the whole pool";
    const relaxNote = relaxed ? ` <span class="small">(no exact match — ${relaxed})</span>` : "";
    a.innerHTML = `<p class="answer-note">${parsed} — ${poolSize.toLocaleString()} candidates matched,
      top ${results.length} ranked against <b>${esc(TL.club.name)}</b>'s ${TL.club.style} model.${relaxNote}</p>`
      + results.map(ev => cardHTML(ev)).join("");
  }

  function renderSimilar(anchor, a) {
    const sims = E.similarTo(anchor);
    a.innerHTML = `<p class="answer-note">Nearest neighbours to <b>${esc(anchor.name)}</b>
      (${anchor.posLabel}, ${esc(anchor.club)}) by cosine similarity over the 13-attribute vector:</p>`
      + sims.map(ev => cardHTML(ev, `similarity ${ev.similarity}%`)).join("");
  }

  function renderReport(ev, a) {
    const paras = E.writeReport(ev);
    a.innerHTML = `<div class="report">`
      + paras.map((p, i) => `<p class="${i === paras.length - 1 ? "verdict" : ""}">${esc(p)}</p>`).join("")
      + `</div>` + cardHTML(ev);
  }

  function renderCompare(pair, a) {
    a.innerHTML = `<p class="answer-note">Head-to-head against ${esc(TL.club.name)}'s profile — expand any bar for the reasoning.</p>`
      + pair.map(p => cardHTML(E.evaluate(p, { club: TL.club }))).join("");
  }

  function renderMarket(a) {
    const items = E.marketWatch();
    if (!items.length) {
      a.innerHTML = `<p class="answer-note">No signals fired for this squad right now.</p>`;
      return;
    }
    a.innerHTML = `<p class="answer-note">Market watch — driven by <b>real</b> three-season minutes and output
      trends (no market values: Transfermarkt data isn't available in this build, so nothing here is invented):</p>`
      + items.map(it => `<div class="sig"><span class="tag tag--${it.kind}">${it.kind}</span>
          <span>${esc(it.text)} <span class="small">(fit vs. us: ${Math.round(it.score)}/100)</span></span></div>`).join("");
  }

  function renderSquad(a) {
    const rows = E.squadAnalysis();
    a.innerHTML = `<p class="answer-note">Squad audit for <b>${esc(TL.club.name)}</b> —
      quality is the line's average attribute rating across ${TL.club.squad.length} players in the database:</p>
      <table class="sq"><tr><th>Line</th><th>Players</th><th>Quality</th><th>Avg age</th><th>Verdict</th></tr>`
      + rows.map(r => {
        const cls = /priority|thin|no players/.test(r.flag) ? "flag-bad"
          : /ageing/.test(r.flag) ? "flag-warn" : "flag-ok";
        return `<tr><td>${r.line}</td><td>${r.count}</td><td>${r.quality || "—"}</td>
                <td>${r.age || "—"}</td><td class="${cls}">${r.flag}</td></tr>`;
      }).join("") + `</table>`;
  }

  /* ---------- player card ---------- */
  function cardHTML(ev, extraMeta) {
    const p = ev.player;
    const cls = ev.overall >= 75 ? "s-hi" : ev.overall >= 60 ? "s-md" : "s-lo";
    const conf = TL.CONF[p.conf];
    const bars = E.SCORING.map(k => {
      const part = ev.parts[k];
      const bcls = part.score >= 70 ? "" : part.score >= 50 ? "mid" : "low";
      return `<div class="bar ${bcls}" data-model="${k}" data-pid="${p.id}" title="Click for the reasoning">
        <div class="lbl"><span>${E.MODELS[k].label}</span><span>${part.score}</span></div>
        <div class="track"><div class="fill" style="width:${part.score}%"></div></div>
      </div>`;
    }).join("");
    return `<div class="pcard" data-pid="${p.id}">
      <div class="pcard-top">
        <div><span class="nm">${esc(p.name)}</span>
          <span class="conf conf--${p.conf}" title="${esc(conf.tip)}">${conf.label}</span>
          <div class="meta">${p.posLabel} · ${p.age}y · ${p.foot}-footed · ${esc(p.nation)} ·
            ${esc(p.club)} (${esc(p.league)})${p.conf ? ` · ${p.minutes} min` : ""}${extraMeta ? " · " + extraMeta : ""}</div>
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

  /* one delegated listener on the feed handles every card, present and future */
  function wireCards(scope) {
    scope.addEventListener("click", (e) => {
      const bar = e.target.closest(".bar");
      if (bar) {
        const p = TL.players[+bar.dataset.pid];
        const part = E.evaluate(p, { club: TL.club }).parts[bar.dataset.model];
        const why = bar.closest(".bars").querySelector(".why");
        why.classList.add("open");
        why.innerHTML = `<b>${E.MODELS[bar.dataset.model].label} → ${part.score}/100.</b> ${part.why.map(esc).join(" · ")}`;
        return;
      }
      const btn = e.target.closest("[data-act]");
      if (btn) {
        const p = TL.players[+btn.dataset.pid];
        $("#q").value = btn.dataset.act === "report"
          ? `scout report on ${p.name}` : `find players similar to ${p.name}`;
        ask();
      }
    });
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }
})();
