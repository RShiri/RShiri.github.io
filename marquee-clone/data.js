/* ===========================================================================
   Touchline — data layer.
   Loads the real player database built by build_players.py. No synthetic
   players: every name, club, league and minute below comes from public data.
   See RESEARCH.md for sources and known limitations.
   =========================================================================== */
"use strict";

const TL = window.TL = window.TL || {};

/* short JSON keys -> the attribute names the engine and UI use */
TL.ATTR_LABELS = {
  pace: "Pace", stamina: "Stamina", strength: "Strength", control: "Ball control",
  dribbling: "Dribbling", passing: "Passing", vision: "Vision", finishing: "Finishing",
  aerial: "Aerial", defending: "Defending", pressing: "Pressing",
  positioning: "Positioning", composure: "Composure"
};
TL.ATTR_KEYS = Object.keys(TL.ATTR_LABELS);
const SHORT = {};
TL.ATTR_KEYS.forEach(k => { SHORT[k] = k.slice(0, 4); });

TL.CONF = {
  2: { label: "Verified", tip: "Ratings driven by a full season of Big-5 match data" },
  1: { label: "Partial", tip: "Matched to match data, but a small minutes sample" },
  0: { label: "Baseline", tip: "EA FC 24 baseline — no recent public match data for this league" }
};

/* ---- load & decode the columnar payload ---- */
TL.load = async function () {
  const res = await fetch("players.json");
  if (!res.ok) throw new Error(`players.json failed to load (${res.status})`);
  const raw = await res.json();
  const ix = {};
  raw.cols.forEach((c, n) => { ix[c] = n; });

  TL.meta = raw.meta;
  TL.players = raw.rows.map((r, id) => {
    const attrs = {};
    for (const k of TL.ATTR_KEYS) attrs[k] = r[ix[SHORT[k]]] ?? 60;
    return {
      id,
      name: r[ix.n], club: r[ix.c] || "—", league: r[ix.l] || "—",
      nation: r[ix.nat] || "—",
      pos: r[ix.p], posLabel: r[ix.pl], line: r[ix.ln],
      age: r[ix.ag], foot: r[ix.ft] || "Right",
      height: r[ix.ht] ?? null,
      value: r[ix.val] ?? null,           // €m, Transfermarkt (Sept 2025); null = unknown
      contractTo: r[ix.cex] ?? null,
      minutes: r[ix.mn] || 0,
      conf: r[ix.cf] || 0,
      minTrend: r[ix.mt] || 0,      // FBref: minutes vs prior seasons (big 5 only)
      formTrend: r[ix.ft_] || 0,
      // global career (all competitions worldwide, 22/23-24/25)
      apps: r[ix.gap] || 0,
      squadApps: r[ix.gsq] || 0,
      goalsAssists: r[ix.gga] || 0,
      startRate: r[ix.grt] ?? null,
      injuryDays: r[ix.inj] || 0,
      appTrend: r[ix.gmt] ?? null,
      outputTrend: r[ix.gft] ?? null,
      valueTrend: r[ix.vtr] ?? null,
      // profile depth
      role: r[ix.role] ?? null,          // Transfermarkt's detailed position
      agent: r[ix.agent] ?? null,
      bornIn: r[ix.born] ?? null,
      joined: r[ix.jn] ?? null,
      isEU: r[ix.eu] ?? null,
      loanFrom: r[ix.loan] ?? null,
      onLoan: !!r[ix.onloan],
      career: r[ix.car] || [],           // [[yyyy-mm, from, to, feeM, type], ...]
      clubCount: r[ix.ncl] ?? null,
      topFee: r[ix.tfee] ?? null,
      leagueStrength: r[ix.lgs] ?? null,
      fcOverall: r[ix.ovr] ?? null,
      attrs
    };
  });

  /* league + club indexes for filtering and the club picker */
  TL.leagues = [...new Set(TL.players.map(p => p.league))].sort();
  const byClub = {};
  for (const p of TL.players) (byClub[p.club] = byClub[p.club] || []).push(p);
  TL.clubsIndex = byClub;
  /* only clubs with a full-ish squad make sensible synergy baselines */
  TL.clubs = Object.keys(byClub).filter(c => byClub[c].length >= 15 && c !== "—").sort();

  TL.setClub(TL.clubs.includes("Arsenal") ? "Arsenal" : TL.clubs[0]);
  return TL;
};

/* ---- "your club": a real squad from the database ---- */
TL.club = { name: null, league: null, style: "high-press", squad: [],
            verifiedOnly: false, budgetM: 60 };

TL.setClub = function (name) {
  const squad = (TL.clubsIndex[name] || []).slice()
    .sort((a, b) => b.minutes - a.minutes);
  TL.club.name = name;
  TL.club.league = squad.length ? squad[0].league : "—";
  TL.club.squad = squad;
  return TL.club;
};
