/* ===========================================================================
   Touchline engine — nine modules over the real player database.
   Eight score and expose their reasoning; the ninth writes the prose.
   Nothing here is a black box: every module returns {score, why[]}.
   =========================================================================== */
"use strict";
(function () {
  const TL = window.TL;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const avg = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
  const pct = (v) => Math.round(v);

  /* ================= the nine models ================= */
  const MODELS = {
    performance: {
      label: "Performance", desc: "Output vs. positional baseline",
      run(p) {
        const core = {
          GK: ["positioning", "composure", "defending"], CB: ["defending", "aerial", "positioning"],
          FB: ["stamina", "defending", "dribbling"], DM: ["defending", "passing", "pressing"],
          CM: ["passing", "stamina", "vision"], AM: ["vision", "passing", "dribbling"],
          WG: ["dribbling", "pace", "finishing"], ST: ["finishing", "positioning", "composure"]
        }[p.pos];
        return { score: pct(avg(core.map(k => p.attrs[k]))),
                 why: core.map(k => `${TL.ATTR_LABELS[k]} ${p.attrs[k]}`) };
      }
    },
    physical: {
      label: "Physical", desc: "Athletic profile",
      run(p) {
        return { score: pct(avg([p.attrs.pace, p.attrs.stamina, p.attrs.strength])),
                 why: [`Pace ${p.attrs.pace}`, `Stamina ${p.attrs.stamina}`, `Strength ${p.attrs.strength}`] };
      }
    },
    technical: {
      label: "Technical", desc: "On-ball quality",
      run(p) {
        return { score: pct(avg([p.attrs.control, p.attrs.dribbling, p.attrs.passing])),
                 why: [`Ball control ${p.attrs.control}`, `Dribbling ${p.attrs.dribbling}`, `Passing ${p.attrs.passing}`] };
      }
    },
    tacticalFit: {
      label: "Tactical fit", desc: "Match to the club's game model",
      run(p, ctx) {
        const map = {
          "high-press": ["pressing", "stamina", "pace"],
          "possession": ["passing", "control", "composure"],
          "transition": ["pace", "dribbling", "finishing"]
        };
        const keys = map[ctx.club.style] || map["high-press"];
        return { score: pct(avg(keys.map(k => p.attrs[k]))),
                 why: keys.map(k => `${TL.ATTR_LABELS[k]} ${p.attrs[k]}`)
                   .concat(`vs. ${ctx.club.style} model`) };
      }
    },
    synergy: {
      label: "Synergy", desc: "Fit with the current squad",
      run(p, ctx) {
        const squad = ctx.club.squad || [];
        if (!squad.length) return { score: 50, why: ["No squad loaded"] };
        const qual = (q) => avg(Object.values(q.attrs));
        const line = squad.filter(q => q.line === p.line);
        const same = squad.filter(q => q.pos === p.pos);
        const mine = qual(p);
        const lineAvg = line.length ? avg(line.map(qual)) : mine;
        const bestSame = same.length ? Math.max(...same.map(qual)) : 0;
        let s = 55 + (mine - lineAvg) * 0.9 - Math.max(0, bestSame - mine) * 0.5;
        const why = [];
        if (mine > lineAvg + 2) why.push(`Raises the ${p.line} line (line avg ${pct(lineAvg)}, player ${pct(mine)})`);
        else why.push(`At or below the ${p.line} line average (${pct(lineAvg)})`);
        if (same.length) {
          why.push(bestSame > mine + 3
            ? `Behind the incumbent ${p.pos} (${pct(bestSame)}) — rotation option`
            : `Competes with the incumbent ${p.pos} (${pct(bestSame)})`);
        } else why.push(`No natural ${p.pos} in the squad — fills a gap`);
        if (p.foot === "Left" && same.length && same.every(q => q.foot !== "Left")) {
          s += 5; why.push("Adds a left-footed option this position lacks");
        }
        return { score: pct(clamp(s, 5, 98)), why };
      }
    },
    potential: {
      label: "Potential", desc: "Age curve + observed trajectory",
      run(p) {
        const base = p.age <= 20 ? 88 : p.age <= 23 ? 78 : p.age <= 26 ? 62 : p.age <= 29 ? 45 : 28;
        const why = [`Age ${p.age}`];
        let s = base;
        if (p.outputTrend != null) {
          s += p.outputTrend * 18;
          why.push(p.outputTrend > 0.08 ? "Goal involvement up on prior seasons"
            : p.outputTrend < -0.08 ? "Goal involvement down on prior seasons"
            : "Output stable across three seasons");
        } else why.push("No appearance record — age curve only");
        return { score: pct(clamp(s, 5, 98)), why };
      }
    },
    momentum: {
      label: "Momentum", desc: "3-season appearance, output & valuation trend",
      run(p) {
        if (p.appTrend == null && !p.apps) {
          return { score: 50, why: ["No appearance record matched for this player"] };
        }
        const at = p.appTrend || 0, ot = p.outputTrend || 0;
        let s = 50 + at * 28 + ot * 22;
        const why = [];
        why.push(at > 0.08 ? `Appearances rising (${p.apps} in 24/25)`
          : at < -0.08 ? `Appearances falling (${p.apps} in 24/25)`
          : `Appearances steady (${p.apps} in 24/25)`);
        why.push(ot > 0.08 ? `Output up (${p.goalsAssists} G+A)` :
          ot < -0.08 ? `Output down (${p.goalsAssists} G+A)` : `Output flat (${p.goalsAssists} G+A)`);
        if (p.valueTrend != null) {
          s += clamp(p.valueTrend, -1, 1) * 10;
          why.push(p.valueTrend > 0.15 ? `Valuation up ${Math.round(p.valueTrend * 100)}% over two years`
            : p.valueTrend < -0.15 ? `Valuation down ${Math.round(-p.valueTrend * 100)}% over two years`
            : "Valuation broadly flat");
        }
        return { score: pct(clamp(s, 5, 98)), why };
      }
    },
    level: {
      label: "Level", desc: "Strength of the competition he plays in",
      run(p) {
        if (p.leagueStrength == null) {
          return { score: 45, why: [`${p.league} is not covered by the strength index — treat the ratings as unbenchmarked`] };
        }
        const s = p.leagueStrength;
        const band = s >= 85 ? "a top-tier competition" : s >= 65 ? "a strong competition"
          : s >= 45 ? "a mid-tier competition" : "a lower-tier competition";
        return { score: pct(s),
                 why: [`${p.league} rates ${s}/100 on squad valuation`, `${band} — output here does not translate 1:1 to a stronger league`] };
      }
    },
    value: {
      label: "Market value", desc: "Real fee vs. budget & contract leverage",
      run(p, ctx) {
        if (p.value == null) {
          return { score: 50, why: ["No Transfermarkt valuation for this player — score held neutral rather than guessed"] };
        }
        const b = ctx.club.budgetM;
        let s = p.value <= b * 0.4 ? 92 : p.value <= b * 0.75 ? 78
              : p.value <= b ? 64 : p.value <= b * 1.5 ? 34 : 12;
        const why = [`Valued €${p.value}m vs €${b}m budget`];
        if (p.contractTo) {
          const yrs = p.contractTo - 2025;
          if (yrs <= 0) { s = clamp(s + 18, 0, 98); why.push(`Contract expired/expiring ${p.contractTo} — minimal fee leverage for the selling club`); }
          else if (yrs === 1) { s = clamp(s + 12, 0, 98); why.push(`Contract runs to ${p.contractTo} — one year left, selling club under pressure`); }
          else why.push(`Contract to ${p.contractTo}`);
        } else why.push("Contract end unknown");
        return { score: pct(s), why };
      }
    },
    availability: {
      label: "Availability", desc: "Selection rate & real injury record",
      run(p) {
        if (!p.squadApps && !p.conf) {
          return { score: 50, why: ["No appearance or injury record matched"] };
        }
        const why = [];
        let s;
        if (p.squadApps) {
          // share of matchday squads he actually played in, across all competitions
          const rate = p.startRate != null ? p.startRate : p.apps / p.squadApps;
          s = clamp(rate * 100, 0, 100);
          why.push(`${p.apps} appearances from ${p.squadApps} matchday squads (${Math.round(rate * 100)}%)`);
        } else {
          s = clamp(p.minutes / 3060 * 100, 0, 100);
          why.push(`${p.minutes} league minutes`);
        }
        if (p.injuryDays > 0) {
          s -= clamp(p.injuryDays / 12, 0, 45);
          why.push(`${p.injuryDays} days missed to injury across three seasons`);
        } else why.push("No injury record in the last three seasons");
        return { score: pct(clamp(s, 5, 98)), why };
      }
    },
    language: {
      label: "Report writer", desc: "Writes the prose (does not score)",
      run() { return { score: 0, why: ["Turns the eight scores into the written report"] }; }
    }
  };

  const SCORING = ["performance", "physical", "technical", "tacticalFit",
                   "synergy", "potential", "momentum", "level", "value", "availability"];

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

  /* ================= NL query parser ================= */
  const POS_WORDS = [
    [/goal\s?keeper|keeper|\bgk\b/, "GK"],
    [/centre[- ]?back|center[- ]?back|\bcb\b|central defender/, "CB"],
    [/full[- ]?back|wing[- ]?back|\bfb\b|left[- ]?back|right[- ]?back/, "FB"],
    [/defensive mid|holding mid|\bdm\b|anchor|number (six|6)/, "DM"],
    [/central mid|centre mid|box[- ]to[- ]box|\bcm\b|number (eight|8)/, "CM"],
    [/attacking mid|playmaker|\bam\b|number (ten|10)/, "AM"],
    [/winger|wide (forward|man)|\bwg\b/, "WG"],
    [/striker|forward|number (nine|9)|\bst\b|goalscorer/, "ST"]];

  const TRAIT_WORDS = [
    [/\btall\b|aerial|good in the air|header/, "aerial", f => { f.minAttr.aerial = 72; f.boost.aerial = 2; }],
    [/\bfast\b|\bquick\b|pacey|rapid|speed/, "pace", f => { f.minAttr.pace = 78; f.boost.pace = 2; }],
    [/ball control|good feet|technical|first touch/, "ball control", f => { f.minAttr.control = 72; f.boost.control = 2; }],
    [/dribbl/, "dribbling", f => { f.minAttr.dribbling = 74; f.boost.dribbling = 2; }],
    [/press(ing|er)?|work[- ]?rate|engine|intensity/, "pressing", f => { f.minAttr.pressing = 70; f.boost.pressing = 2; }],
    [/passer|passing|distribution|ball[- ]playing/, "passing", f => { f.minAttr.passing = 74; f.boost.passing = 2; }],
    [/creat(ive|or)|vision|final ball|chance creation/, "creativity", f => { f.minAttr.vision = 74; f.boost.vision = 2; }],
    [/finish(er|ing)|clinical|goal[- ]?scor|scores/, "finishing", f => { f.minAttr.finishing = 74; f.boost.finishing = 2; }],
    [/strong|physical|robust|powerful/, "physicality", f => { f.minAttr.strength = 72; f.boost.strength = 2; }],
    [/defend|defensive|tackl|solid at the back/, "defending", f => { f.minAttr.defending = 72; f.boost.defending = 2; }],
    [/left[- ]?foot/, "left-footed", f => { f.foot = "Left"; }],
    [/young|prospect|talent|wonderkid|u2[0123]|under[- ]?2[0123]/, "young", f => { f.maxAge = Math.min(f.maxAge || 99, 23); }],
    [/experienc|veteran/, "experienced", f => { f.minAge = 28; }],
    [/regular|starter|plays every week|nailed/, "regular starter", f => { f.minStartRate = 0.7; }],
    [/durab|injury[- ]?free|robust|never injured|reliable fitness/, "durable", f => { f.durableOnly = true; }],
    [/breakout|breakthrough|emerging|rising/, "rising", f => { f.risingOnly = true; }],
    [/expiring|free agent|out of contract|contract (ends|expir)|final year/, "expiring contract", f => { f.maxContract = 2026; }],
    [/cheap|bargain|budget|affordable|low fee/, "value buy", f => { f.maxValue = Math.min(f.maxValue || 1e9, TL.club.budgetM * 0.5); }],
    [/verified|proven|with data|reliable data/, "verified data only", f => { f.verifiedOnly = true; }]];

  function parseQuery(text) {
    const q = text.toLowerCase();
    const f = { minAttr: {}, boost: {}, notes: [] };
    const intent = { type: "shortlist", filters: f };

    const named = findPlayers(q);
    if (/compare/.test(q) && named.length >= 2) { intent.type = "compare"; intent.pair = named.slice(0, 2); return intent; }
    if (/similar to|like\s|replace|alternative to/.test(q) && named.length) { intent.type = "similar"; intent.anchor = named[0]; return intent; }
    if (named.length && /\bprofile\b|full profile|everything (on|about)|dossier/.test(q)) { intent.type = "profile"; intent.anchor = named[0]; return intent; }
    if (named.length && /report|tell me about|scout|who is/.test(q)) { intent.type = "report"; intent.anchor = named[0]; return intent; }
    if (named.length && q.trim().split(/\s+/).length <= 4) { intent.type = "report"; intent.anchor = named[0]; return intent; }
    if (/market|watch|opportunit|hidden gem|undervalued/.test(q) && !/striker|winger|back|mid|keeper/.test(q)) { intent.type = "market"; return intent; }
    if (/my squad|our squad|squad (depth|analysis|planning|audit)|weak(nesses)? in (my|our)|where do we|where is my/.test(q)) { intent.type = "squad"; return intent; }

    for (const [re, pos] of POS_WORDS) if (re.test(q)) { f.pos = pos; f.notes.push(`position: ${pos}`); break; }
    // a bare "midfielder"/"defender"/"forward" still constrains the line
    if (!f.pos) {
      for (const [re, line] of [[/midfield/, "MID"], [/defender|defence|defense|at the back/, "DEF"],
                                [/forward|attacker|up front/, "ATT"]]) {
        if (re.test(q)) { f.line = line; f.notes.push(`line: ${line}`); break; }
      }
    }
    for (const [re, label, apply] of TRAIT_WORDS) if (re.test(q)) { apply(f); f.notes.push(label); }

    // "under 23" is an age; "under €20m" / "under 20m" is a fee
    const feeM = q.match(/(?:under|below|max|up to)\s*€?\s*(\d+(?:\.\d+)?)\s*m\b/)
              || q.match(/budget\s*(?:of)?\s*€?\s*(\d+(?:\.\d+)?)\s*m\b/);
    if (feeM) { f.maxValue = +feeM[1]; f.notes.push(`fee ≤ €${feeM[1]}m`); }
    const ageM = q.match(/under\s+(\d{2})\b(?!\s*m)/);
    if (ageM && +ageM[1] <= 40) { f.maxAge = +ageM[1]; f.notes.push(`age ≤ ${ageM[1]}`); }

    const league = TL.leagues.find(L => L !== "—" && q.includes(L.toLowerCase()));
    if (league) { f.league = league; f.notes.push(league); }
    const nation = [...new Set(TL.players.map(p => p.nation))]
      .find(n => n && n !== "—" && new RegExp(`\\b${n.toLowerCase()}\\b`).test(q));
    if (nation) { f.nation = nation; f.notes.push(nation); }
    return intent;
  }

  function findPlayers(q) {
    const hits = [];
    for (const p of TL.players) {
      const n = p.name.toLowerCase();
      if (q.includes(n)) hits.push({ p, len: n.length });
    }
    hits.sort((a, b) => b.len - a.len);
    return hits.map(h => h.p);
  }

  /* ================= retrieval ================= */
  function shortlist(filters, n = 6) {
    const excludeOwn = new Set((TL.club.squad || []).map(p => p.id));
    let pool = TL.players.filter(p => !excludeOwn.has(p.id));
    if (filters.pos) pool = pool.filter(p => p.pos === filters.pos);
    if (filters.line) pool = pool.filter(p => p.line === filters.line);
    if (filters.maxAge) pool = pool.filter(p => p.age <= filters.maxAge);
    if (filters.minAge) pool = pool.filter(p => p.age >= filters.minAge);
    if (filters.foot) pool = pool.filter(p => p.foot === filters.foot);
    if (filters.league) pool = pool.filter(p => p.league === filters.league);
    if (filters.nation) pool = pool.filter(p => p.nation === filters.nation);
    if (filters.minStartRate) pool = pool.filter(p =>
      (p.startRate != null && p.startRate >= filters.minStartRate && p.apps >= 15)
      || p.minutes >= 1800);
    if (filters.maxValue) pool = pool.filter(p => p.value != null && p.value <= filters.maxValue);
    if (filters.maxContract) pool = pool.filter(p => p.contractTo != null && p.contractTo <= filters.maxContract);
    if (filters.risingOnly) pool = pool.filter(p => p.age <= 24 &&
      ((p.appTrend != null && p.appTrend > 0.15) || (p.valueTrend != null && p.valueTrend > 0.3)));
    if (filters.durableOnly) pool = pool.filter(p => p.injuryDays <= 30 && p.squadApps > 0);
    if (filters.verifiedOnly || TL.club.verifiedOnly) pool = pool.filter(p => p.conf === 2);
    for (const [k, v] of Object.entries(filters.minAttr)) pool = pool.filter(p => p.attrs[k] >= v);

    let relaxed = null;
    if (!pool.length) {
      relaxed = "attribute thresholds relaxed";
      pool = TL.players.filter(p => !excludeOwn.has(p.id)
        && (!filters.pos || p.pos === filters.pos)
        && (!filters.line || p.line === filters.line)
        && (!filters.maxValue || (p.value != null && p.value <= filters.maxValue))
        && (!filters.maxContract || (p.contractTo != null && p.contractTo <= filters.maxContract))
        && (!filters.maxAge || p.age <= filters.maxAge)
        && (!filters.foot || p.foot === filters.foot)
        && (!filters.league || p.league === filters.league)
        && (!(filters.verifiedOnly || TL.club.verifiedOnly) || p.conf === 2));
    }

    const ctx = { club: TL.club };
    const weights = { performance: 1.2, tacticalFit: 1.2, synergy: 1.1 };
    const scored = pool.map(p => {
      const ev = evaluate(p, ctx, weights);
      let bonus = 0;
      for (const [k, w] of Object.entries(filters.boost)) bonus += (p.attrs[k] - 70) * 0.12 * w;
      ev.overall = Math.round(clamp(ev.overall + bonus, 0, 99));
      return ev;
    });
    scored.sort((a, b) => (b.overall - a.overall) || (b.player.conf - a.player.conf));
    return { results: scored.slice(0, n), poolSize: pool.length, relaxed };
  }

  function similarTo(anchor, n = 6) {
    const va = TL.ATTR_KEYS.map(k => anchor.attrs[k]);
    const na = Math.hypot(...va);
    const scored = TL.players
      .filter(p => p.id !== anchor.id && p.pos === anchor.pos)
      .map(p => {
        const vb = TL.ATTR_KEYS.map(k => p.attrs[k]);
        const dot = va.reduce((s, x, i) => s + x * vb[i], 0);
        const ev = evaluate(p, { club: TL.club });
        ev.similarity = Math.round(dot / (na * Math.hypot(...vb)) * 100);
        return ev;
      });
    scored.sort((a, b) => b.similarity - a.similarity);
    return scored.slice(0, n);
  }

  /* ================= market watch (real signals only) ================= */
  function marketWatch(n = 8) {
    const own = new Set((TL.club.squad || []).map(p => p.id));
    const items = [];
    for (const p of TL.players) {
      if (own.has(p.id)) continue;
      const q = avg(Object.values(p.attrs));
      // contract signals are the strongest real lever and don't need match data
      if (p.contractTo != null && p.contractTo <= 2026 && q >= 66 && p.value != null) {
        items.push({ p, kind: "Contract", score: q + 8,
          text: `${p.name} (${p.posLabel}, ${p.club}) is into the final stretch of his deal — expires ${p.contractTo}. Valued €${p.value}m, and the selling club's leverage drops every month.` });
        continue;
      }
      if (p.appTrend != null && p.appTrend < -0.2 && q >= 66)
        items.push({ p, kind: "Minutes", score: q,
          text: `${p.name} (${p.posLabel}, ${p.club}) saw game time collapse against his prior seasons — ${p.apps} appearances from ${p.squadApps} matchday squads — despite a ${Math.round(q)}-rated profile. Classic unsettled-starter window.` });
      else if (p.valueTrend != null && p.valueTrend > 0.5 && p.age <= 24)
        items.push({ p, kind: "Form", score: q + 6,
          text: `${p.name} (${p.age}, ${p.club}) has seen his valuation climb ${Math.round(p.valueTrend * 100)}% in two years on ${p.goalsAssists} goal involvements. The market is already moving in ${p.league}.` });
      else if (p.appTrend != null && p.appTrend > 0.35 && p.age <= 23)
        items.push({ p, kind: "Breakout", score: q + 4,
          text: `${p.name} (${p.age}, ${p.club}) went from fringe to ${p.apps} appearances — a genuine breakthrough season in ${p.league}.` });
    }
    items.sort((a, b) => b.score - a.score);
    return items.slice(0, n);
  }

  /* ================= squad audit ================= */
  function squadAnalysis() {
    const out = [];
    for (const line of ["GK", "DEF", "MID", "ATT"]) {
      const ps = (TL.club.squad || []).filter(p => p.line === line);
      if (!ps.length) { out.push({ line, count: 0, quality: 0, age: 0, flag: "no players in database" }); continue; }
      const q = Math.round(avg(ps.map(p => avg(Object.values(p.attrs)))));
      const age = Math.round(avg(ps.map(p => p.age)));
      const flag = ps.length < 3 ? "thin — needs depth"
        : q < 62 ? "priority to strengthen"
        : age >= 29 ? "ageing — plan succession" : "adequate depth";
      out.push({ line, count: ps.length, quality: q, age, flag, players: ps });
    }
    return out;
  }

  /* ================= report writer ================= */
  function tier(s) { return s >= 82 ? "elite" : s >= 70 ? "strong" : s >= 55 ? "solid" : s >= 40 ? "below-par" : "weak"; }

  function writeReport(ev) {
    const p = ev.player, P = ev.parts, paras = [];
    const conf = TL.CONF[p.conf];
    const bio = [`${p.age}-year-old`, `${p.foot.toLowerCase()}-footed`,
                 p.height ? `${p.height}cm` : null].filter(Boolean).join(" ");
    paras.push(`${p.name} is a ${bio} ${p.posLabel.toLowerCase()} at ${p.club} (${p.league}), ${p.nation} by nationality${p.value != null ? `, valued at €${p.value}m` : ""}${p.contractTo ? ` with a contract to ${p.contractTo}` : ""}. Overall rating against ${TL.club.name}'s profile: ${ev.overall}/100. Data confidence: ${conf.label.toLowerCase()} — ${conf.tip.toLowerCase()}.`);
    paras.push(`On the pitch, the performance model grades him ${tier(P.performance.score)} (${P.performance.score}) for his position, driven by ${P.performance.why.slice(0, 2).join(" and ")}. Physically he rates ${P.physical.score} (${P.physical.why.join(", ")}); technically ${P.technical.score} (${P.technical.why.join(", ")}).`);
    paras.push(`Fit: against our ${TL.club.style} game model the tactical-fit score is ${P.tacticalFit.score}/100 (${P.tacticalFit.why.join("; ")}). Squad synergy is ${P.synergy.score}/100 — ${P.synergy.why.join("; ")}.`);
    paras.push(`Cost: ${P.value.why.join("; ")} — market score ${P.value.score}/100. Level: ${P.level.why.join("; ")}.`);
    if (p.career && p.career.length) {
      const path = p.career.map(m => `${m[0]} ${m[1]} → ${m[2]}${m[3] > 0 ? ` (€${m[3]}m)` : m[4] === "Loan" ? " (loan)" : " (free)"}`).join("; ");
      paras.push(`Career: ${path}.${p.clubCount ? ` ${p.clubCount} senior clubs to date.` : ""}${p.topFee ? ` Highest fee paid for him: €${p.topFee}m.` : ""}${p.onLoan ? " Currently out on loan." : ""}${p.agent ? ` Represented by ${p.agent}.` : ""}`);
    }
    paras.push(`Trajectory: momentum reads ${P.momentum.score}/100 (${P.momentum.why.join("; ")}), availability ${P.availability.score}/100 (${P.availability.why.join(", ")}), and the potential model ${P.potential.score}/100 — ${P.potential.why.join("; ")}.`);
    if (!p.conf) {
      paras.push(`Caveat: ${p.league} has no public event data in this build, so while the appearance, injury and valuation record above is real, the attribute ratings themselves rest on the EA FC 24 baseline. Treat those as a lead to verify with video, not a measured read.`);
    }
    paras.push(ev.overall >= 75
      ? `Recommendation: pursue. The profile clears our bar on fit and output, and the reasoning holds across every scoring model.`
      : ev.overall >= 60
      ? `Recommendation: monitor. A genuine option, but at least one model flags a caveat worth tracking across the next window.`
      : `Recommendation: pass. The profile does not clear our thresholds against this squad and game model.`);
    return paras;
  }

  TL.engine = { MODELS, SCORING, evaluate, parseQuery, shortlist, similarTo,
                writeReport, marketWatch, squadAnalysis, tier };
})();
