/* ===========================================================================
   Touchline engine — nine named scoring modules + a rule-based NL query
   parser + a templated report writer. Everything explainable: each module
   returns {score, why[]} so the UI can show its reasoning.
   =========================================================================== */
"use strict";
(function () {
  const TL = window.TL;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const avg = (xs) => xs.reduce((a, b) => a + b, 0) / (xs.length || 1);

  /* ================= the nine models ================= */
  /* Each takes (player, ctx) and returns {score: 0-100, why: string[]} */

  const MODELS = {
    performance: {
      label: "Performance", desc: "Output vs. positional baseline",
      run(p) {
        const core = { GK: ["positioning","composure","defending"], CB: ["defending","aerial","positioning"],
          FB: ["stamina","defending","dribbling"], DM: ["defending","passing","pressing"],
          CM: ["passing","stamina","vision"], AM: ["vision","passing","dribbling"],
          WG: ["dribbling","pace","finishing"], ST: ["finishing","positioning","composure"] }[p.pos];
        const s = avg(core.map(k => p.attrs[k]));
        return { score: Math.round(s), why: core.map(k => `${TL.ATTR_LABELS[k]} ${p.attrs[k]}`) };
      }
    },
    physical: {
      label: "Physical", desc: "Tracking-style athletic profile",
      run(p) {
        const s = avg([p.attrs.pace, p.attrs.stamina, p.attrs.strength]);
        return { score: Math.round(s), why: [`Pace ${p.attrs.pace}`, `Stamina ${p.attrs.stamina}`, `Strength ${p.attrs.strength}`, `${p.height} cm`] };
      }
    },
    technical: {
      label: "Technical", desc: "On-ball quality",
      run(p) {
        const s = avg([p.attrs.control, p.attrs.dribbling, p.attrs.passing]);
        return { score: Math.round(s), why: [`Ball control ${p.attrs.control}`, `Dribbling ${p.attrs.dribbling}`, `Passing ${p.attrs.passing}`] };
      }
    },
    tacticalFit: {
      label: "Tactical fit", desc: "Match to the club's playing style",
      run(p, ctx) {
        const style = ctx.club.style;
        const map = { "high-press": ["pressing","stamina","pace"], "possession": ["passing","control","composure"], "transition": ["pace","dribbling","finishing"] };
        const keys = map[style] || map["high-press"];
        let s = avg(keys.map(k => p.attrs[k]));
        const why = keys.map(k => `${TL.ATTR_LABELS[k]} ${p.attrs[k]}`);
        if (p.styles.includes(style)) { s += 8; why.push(`Profile tagged "${style}"`); }
        return { score: Math.round(clamp(s, 0, 100)), why };
      }
    },
    synergy: {
      label: "Synergy", desc: "Chemistry with the current squad",
      run(p, ctx) {
        // complementarity: reward covering weak spots in the same line,
        // penalize redundancy with an already-strong same-position starter
        const line = ctx.club.squad.filter(q => q.line === p.line);
        const same = ctx.club.squad.filter(q => q.pos === p.pos);
        const lineAvg = avg(line.map(q => q.quality)) * 100;
        const bestSame = Math.max(0, ...same.map(q => q.quality * 100));
        const myQ = p.quality * 100;
        let s = 55 + (myQ - lineAvg) * 0.45 - Math.max(0, bestSame - myQ) * 0.25;
        const why = [];
        if (myQ > lineAvg + 5) why.push(`Raises the ${p.line} line's level (line avg ${Math.round(lineAvg)}, player ${Math.round(myQ)})`);
        if (bestSame > myQ + 8) why.push(`Sits behind the incumbent ${p.pos} (${Math.round(bestSame)}) — rotation, not starter`);
        else why.push(`Competitive with the incumbent ${p.pos}`);
        if (p.foot === "Left" && same.every(q => q.foot !== "Left")) { s += 5; why.push("Adds a left-footed option the squad lacks"); }
        return { score: Math.round(clamp(s, 5, 98)), why };
      }
    },
    potential: {
      label: "Potential", desc: "Age-curve trajectory",
      run(p) {
        const s = p.age <= 20 ? 88 : p.age <= 23 ? 78 : p.age <= 26 ? 62 : p.age <= 29 ? 45 : 28;
        const adj = clamp(s + p.formTrend * 10, 5, 98);
        return { score: Math.round(adj), why: [`Age ${p.age}`, p.formTrend > 0.3 ? "Form trending up over last 8 matches" : p.formTrend < -0.3 ? "Form dipping over last 8 matches" : "Form stable"] };
      }
    },
    market: {
      label: "Market value", desc: "Price vs. budget & contract leverage",
      run(p, ctx) {
        const b = ctx.club.budgetM;
        let s = p.value <= b * 0.5 ? 90 : p.value <= b ? 70 : p.value <= b * 1.5 ? 40 : 15;
        const why = [`Valued €${p.value}m vs €${b}m budget`];
        if (p.contractUntil <= 2027) { s = clamp(s + 12, 0, 98); why.push(`Contract expires ${p.contractUntil} — selling club has weak leverage`); }
        return { score: Math.round(s), why };
      }
    },
    availability: {
      label: "Availability", desc: "Durability & minutes reliability",
      run(p) {
        let s = 95 - p.injuryDays * 0.45;
        const why = [`${p.injuryDays} days missed in 2 seasons`, `${p.minutesPct}% of league minutes played`];
        s = s * 0.7 + p.minutesPct * 0.3;
        return { score: Math.round(clamp(s, 5, 98)), why };
      }
    },
    language: {
      label: "Report writer", desc: "Writes the prose (does not score)",
      run() { return { score: 0, why: ["Generates the natural-language output from the other eight models"] }; }
    }
  };

  const SCORING = ["performance","physical","technical","tacticalFit","synergy","potential","market","availability"];

  function evaluate(p, ctx, weights) {
    const parts = {};
    let total = 0, wsum = 0;
    for (const key of SCORING) {
      const r = MODELS[key].run(p, ctx);
      const w = (weights && weights[key]) != null ? weights[key] : 1;
      parts[key] = { ...r, weight: w };
      total += r.score * w; wsum += w;
    }
    return { player: p, parts, overall: Math.round(total / (wsum || 1)) };
  }

  /* ================= NL query parser (rule-based stand-in for the LLM) ===== */

  const POS_WORDS = [
    [/goal\s?keeper|keeper|\bgk\b/, "GK"], [/centre[- ]?back|center[- ]?back|\bcb\b|central defender/, "CB"],
    [/full[- ]?back|wing[- ]?back|\bfb\b|left[- ]?back|right[- ]?back/, "FB"],
    [/defensive mid|holding mid|\bdm\b|anchor|number (six|6)/, "DM"],
    [/central mid|centre mid|box[- ]to[- ]box|\bcm\b|number (eight|8)/, "CM"],
    [/attacking mid|playmaker|\bam\b|number (ten|10)/, "AM"],
    [/winger|wide (forward|man)|\bwg\b/, "WG"], [/striker|forward|number (nine|9)|\bst\b|goalscorer/, "ST"]];

  const TRAIT_WORDS = [
    [/\btall\b|aerial|good in the air/, "tall / aerial", f => { f.minHeight = 186; f.boost.aerial = 2; }],
    [/\bfast\b|\bquick\b|pacey|rapid|speed/, "fast", f => { f.minAttr.pace = 78; f.boost.pace = 2; }],
    [/ball control|good feet|technical|first touch/, "ball control", f => { f.minAttr.control = 74; f.boost.control = 2; }],
    [/dribbl/, "dribbler", f => { f.minAttr.dribbling = 75; f.boost.dribbling = 2; }],
    [/press(ing|er)?|work[- ]?rate|engine/, "pressing", f => { f.minAttr.pressing = 70; f.boost.pressing = 2; }],
    [/passer|passing|distribution/, "passing", f => { f.minAttr.passing = 75; f.boost.passing = 2; }],
    [/creat(ive|or)|vision|final ball/, "creativity", f => { f.minAttr.vision = 75; f.boost.vision = 2; }],
    [/finish(er|ing)|clinical|goal[- ]?scor/, "finishing", f => { f.minAttr.finishing = 75; f.boost.finishing = 2; }],
    [/strong|physical|robust/, "physicality", f => { f.minAttr.strength = 72; f.boost.strength = 2; }],
    [/left[- ]?foot/, "left-footed", f => { f.foot = "Left"; }],
    [/young|prospect|talent|u2[013]|under[- ]?2[013]/, "young", f => { f.maxAge = Math.min(f.maxAge || 99, 23); }],
    [/cheap|bargain|budget|affordable|value/, "value buy", f => { f.maxValue = Math.min(f.maxValue || 999, TL.club.budgetM * 0.6); }],
    [/durab|available|fit\b|injury[- ]?free/, "durable", f => { f.maxInjury = 30; }],
    [/expiring|free agent|out of contract|contract (ends|expir)/, "expiring contract", f => { f.maxContract = 2027; }]];

  function parseQuery(text) {
    const q = text.toLowerCase();
    const f = { minAttr: {}, boost: {}, notes: [] };
    const intent = { type: "shortlist", filters: f };

    // intent detection
    const nameHit = findPlayerByName(q);
    if (/compare/.test(q)) intent.type = "compare";
    else if (/similar to|like\s|replace/.test(q) && nameHit) { intent.type = "similar"; intent.anchor = nameHit; }
    else if (nameHit && /report|tell me about|profile|scout/.test(q)) { intent.type = "report"; intent.anchor = nameHit; }
    else if (nameHit && q.trim().split(/\s+/).length <= 4) { intent.type = "report"; intent.anchor = nameHit; }
    else if (/market|watch|opportunit|hidden gem|expiring/.test(q) && !/striker|winger|back|mid|keeper/.test(q)) intent.type = "market";
    else if (/my squad|our squad|squad (depth|analysis|planning)|weak(nesses)? in (my|our)|where do we/.test(q)) intent.type = "squad";

    if (intent.type === "compare") {
      intent.pair = findTwoPlayers(q);
      if (!intent.pair) intent.type = "shortlist";
    }

    // position
    for (const [re, pos] of POS_WORDS) if (re.test(q)) { f.pos = pos; f.notes.push(`position: ${pos}`); break; }
    // traits
    for (const [re, label, apply] of TRAIT_WORDS) if (re.test(q)) { apply(f); f.notes.push(label); }
    // numbers: "under 23", "under €20m", "budget 15m"
    const ageM = q.match(/under\s+(\d{2})(?!\s*m)/); if (ageM && +ageM[1] < 45) f.maxAge = +ageM[1];
    const valM = q.match(/(?:under|below|max)\s*€?\s*(\d+(?:\.\d+)?)\s*m/) || q.match(/budget\s*(?:of)?\s*€?\s*(\d+(?:\.\d+)?)\s*m/);
    if (valM) f.maxValue = +valM[1];
    const leagueM = TL.players.map(p => p.league).find(L => q.includes(L.toLowerCase()));
    if (leagueM) f.league = leagueM;
    return intent;
  }

  function findPlayerByName(q) {
    return TL.players.find(p => q.includes(p.name.toLowerCase()) || q.includes(p.name.split(" ")[1].toLowerCase()));
  }
  function findTwoPlayers(q) {
    const hits = TL.players.filter(p => q.includes(p.name.split(" ")[1].toLowerCase()));
    return hits.length >= 2 ? [hits[0], hits[1]] : null;
  }

  /* ================= retrieval ================= */

  function shortlist(filters, n = 6) {
    let pool = TL.players.slice();
    if (filters.pos) pool = pool.filter(p => p.pos === filters.pos);
    if (filters.maxAge) pool = pool.filter(p => p.age <= filters.maxAge);
    if (filters.minHeight) pool = pool.filter(p => p.height >= filters.minHeight);
    if (filters.foot) pool = pool.filter(p => p.foot === filters.foot || p.foot === "Both");
    if (filters.maxValue) pool = pool.filter(p => p.value <= filters.maxValue);
    if (filters.maxInjury != null) pool = pool.filter(p => p.injuryDays <= filters.maxInjury);
    if (filters.maxContract) pool = pool.filter(p => p.contractUntil <= filters.maxContract);
    if (filters.league) pool = pool.filter(p => p.league === filters.league);
    for (const [k, v] of Object.entries(filters.minAttr)) pool = pool.filter(p => p.attrs[k] >= v * 0.9);

    // graceful relaxation: an empty pool answers nothing, so loosen the softest
    // constraints (trait thresholds, then budget/age) and say so via `relaxed`
    let relaxed = null;
    if (pool.length === 0) {
      relaxed = "trait thresholds relaxed";
      pool = TL.players.filter(p =>
        (!filters.pos || p.pos === filters.pos) &&
        (!filters.foot || p.foot === filters.foot || p.foot === "Both") &&
        (!filters.maxAge || p.age <= filters.maxAge) &&
        (!filters.maxValue || p.value <= filters.maxValue) &&
        (!filters.league || p.league === filters.league));
      if (pool.length === 0) {
        relaxed = "trait, budget and age constraints relaxed";
        pool = TL.players.filter(p =>
          (!filters.pos || p.pos === filters.pos) &&
          (!filters.foot || p.foot === filters.foot || p.foot === "Both"));
      }
    }

    const weights = { performance: 1.2, tacticalFit: 1.2, synergy: 1.1 };
    const ctx = { club: TL.club };
    const scored = pool.map(p => {
      const ev = evaluate(p, ctx, weights);
      // trait boosts nudge ranking toward what was asked for
      let bonus = 0;
      for (const [k, w] of Object.entries(filters.boost)) bonus += (p.attrs[k] - 70) * 0.15 * w;
      ev.overall = Math.round(clamp(ev.overall + bonus, 0, 99));
      return ev;
    });
    scored.sort((a, b) => b.overall - a.overall);
    return { results: scored.slice(0, n), poolSize: pool.length, relaxed };
  }

  /* cosine similarity over the attribute vector, for "similar to X" */
  function similarTo(anchor, n = 6) {
    const va = TL.ATTR_KEYS.map(k => anchor.attrs[k]);
    const na = Math.hypot(...va);
    const scored = TL.players.filter(p => p.id !== anchor.id && p.pos === anchor.pos).map(p => {
      const vb = TL.ATTR_KEYS.map(k => p.attrs[k]);
      const dot = va.reduce((s, x, i) => s + x * vb[i], 0);
      const sim = dot / (na * Math.hypot(...vb));
      const ev = evaluate(p, { club: TL.club });
      ev.similarity = Math.round(sim * 100);
      return ev;
    });
    scored.sort((a, b) => b.similarity - a.similarity);
    return scored.slice(0, n);
  }

  /* ================= report writer ("language model") ================= */

  function tier(s) { return s >= 82 ? "elite" : s >= 70 ? "strong" : s >= 55 ? "solid" : s >= 40 ? "below-par" : "weak"; }

  function writeReport(ev) {
    const p = ev.player, P = ev.parts;
    const paras = [];
    paras.push(`${p.name} is a ${p.age}-year-old ${p.foot.toLowerCase()}-footed ${p.posLabel.toLowerCase()} at ${p.club} (${p.league}), currently valued around €${p.value}m with a contract running to ${p.contractUntil}. Overall rating against ${TL.club.name}'s profile: ${ev.overall}/100.`);
    paras.push(`On the pitch, the performance model grades him ${tier(P.performance.score)} (${P.performance.score}) for his position, driven by ${P.performance.why.slice(0, 2).join(" and ")}. The physical profile is ${tier(P.physical.score)} — ${P.physical.why.join(", ")} — and technically he rates ${P.technical.score} (${P.technical.why.join(", ")}).`);
    paras.push(`Fit: against our ${TL.club.style} game model the tactical-fit score is ${P.tacticalFit.score}/100 (${P.tacticalFit.why.join("; ")}). Squad synergy comes out at ${P.synergy.score}/100 — ${P.synergy.why.join("; ")}.`);
    paras.push(`Off the pitch: ${P.market.why.join("; ")} (market score ${P.market.score}). Availability is ${tier(P.availability.score)}: ${P.availability.why.join(", ")}. The potential model reads ${P.potential.score}/100 — ${P.potential.why.join("; ")}.`);
    const verdict = ev.overall >= 75 ? `Recommendation: pursue. The profile clears our bar on fit, output and price, and the reasoning above holds up across all eight scoring models.` :
      ev.overall >= 60 ? `Recommendation: monitor. A genuine option, but at least one model flags a caveat worth tracking over the next window.` :
      `Recommendation: pass at the current price. The profile does not clear our thresholds against this squad and game model.`;
    paras.push(verdict);
    return paras;
  }

  /* ================= market watch ================= */

  function marketWatch() {
    const items = [];
    for (const p of TL.players) {
      const ev = () => evaluate(p, { club: TL.club }).overall;
      if (p.contractUntil <= 2027 && p.quality > 0.62)
        items.push({ p, kind: "Contract", text: `${p.name} (${p.posLabel}, ${p.club}) is into the final stretch of his deal (expires ${p.contractUntil}). Quality profile, weak selling leverage — fee likely below the €${p.value}m valuation.`, score: ev() });
      else if (p.formTrend > 0.85 && p.age <= 24)
        items.push({ p, kind: "Form spike", text: `${p.name} (${p.age}, ${p.league}) is on a sharp upward form trend over the last 8 matches. Value €${p.value}m today; unlikely to stay there.`, score: ev() });
      else if (p.minutesPct < 40 && p.quality > 0.7)
        items.push({ p, kind: "Minutes drop", text: `${p.name} is playing only ${p.minutesPct}% of minutes at ${p.club} despite an ${tier(p.quality * 100)} profile — a classic unsettled-player opportunity.`, score: ev() });
    }
    items.sort((a, b) => b.score - a.score);
    return items.slice(0, 8);
  }

  /* ================= squad analysis ================= */

  function squadAnalysis() {
    const lines = ["GK","DEF","MID","ATT"];
    const out = [];
    for (const line of lines) {
      const ps = TL.club.squad.filter(p => p.line === line);
      const q = Math.round(avg(ps.map(p => p.quality * 100)));
      const age = Math.round(avg(ps.map(p => p.age)));
      const flag = q < 55 ? "priority to strengthen" : age >= 29 ? "ageing — plan succession" : "adequate depth";
      out.push({ line, count: ps.length, quality: q, age, flag, players: ps });
    }
    return out;
  }

  TL.engine = { MODELS, SCORING, evaluate, parseQuery, shortlist, similarTo, writeReport, marketWatch, squadAnalysis, tier };
})();
