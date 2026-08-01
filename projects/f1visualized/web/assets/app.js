/* F1 Visualized dashboard — loads season JSON and renders standings, calendar, results. */
"use strict";

const SEASONS = {};
let current = "2026";

/* ---- team colours (presentation lives in the front-end) ---- */
const TEAM_COLORS = {
  "mclaren": "#ff8000",
  "ferrari": "#e8002d",
  "red bull racing": "#3671c6", "red bull": "#3671c6",
  "mercedes": "#27f4d2",
  "aston martin": "#229971",
  "alpine": "#0093cc",
  "williams": "#1868db",
  "racing bulls": "#6692ff", "rb": "#6692ff", "visa cash app rb": "#6692ff",
  "alphatauri": "#2b4562",
  "haas": "#b6babd", "haas f1 team": "#b6babd",
  "kick sauber": "#52e252", "sauber": "#52e252", "stake f1 team kick sauber": "#52e252",
  "alfa romeo": "#b12039",
  "audi": "#26c1a3",
  "cadillac": "#c9a24b",
};
function teamColor(team) {
  if (!team) return "#8a8a95";
  return TEAM_COLORS[team.trim().toLowerCase()] || "#8a8a95";
}

/* ---- country flags (inline SVG) ---- */
// Race country name -> ISO alpha-2 (for circuit flags).
const COUNTRY_CODE = {
  "abu dhabi": "ae", "united arab emirates": "ae", "australia": "au", "austria": "at",
  "azerbaijan": "az", "bahrain": "bh", "belgium": "be", "brazil": "br", "canada": "ca",
  "china": "cn", "france": "fr", "great britain": "gb", "united kingdom": "gb", "uk": "gb",
  "hungary": "hu", "italy": "it", "japan": "jp", "mexico": "mx", "monaco": "mc",
  "netherlands": "nl", "qatar": "qa", "saudi arabia": "sa", "singapore": "sg",
  "spain": "es", "united states": "us", "usa": "us", "miami": "us", "las vegas": "us",
  "germany": "de", "portugal": "pt", "russia": "ru", "turkey": "tr",
};

// Inline SVG flags — render everywhere (incl. Windows), work offline and in the
// self-contained bundle. Source: file on Pages, or an inlined data URI in the bundle.
function flagSrc(cc) {
  return (window.FLAG_SVGS && window.FLAG_SVGS[cc]) || `assets/flags/${cc}.svg`;
}
function flagImg(cc) {
  if (!cc) return "";
  cc = String(cc).toLowerCase();
  return `<img class="flag" src="${flagSrc(cc)}" alt="" loading="lazy">`;
}
function flag(country) {
  return flagImg(COUNTRY_CODE[(country || "").trim().toLowerCase()]);
}
const natFlag = (cc) => (cc ? flagImg(cc) + " " : "");

const $ = (sel, el = document) => el.querySelector(sel);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmtPts = (p) => (Number.isInteger(p) ? p : (Math.round(p * 10) / 10)).toString();
const swatch = (team, w = 5, h = 18) =>
  `<span class="swatch" style="background:${teamColor(team)};width:${w}px;height:${h}px"></span>`;

/* ---------------- rendering ---------------- */
function data() { return SEASONS[current]; }

function render() {
  const d = data();
  if (!d) return;
  $("#updated").textContent = d.updated
    ? "Updated " + new Date(d.updated).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
    : "";
  renderOverview(d);
  renderStandings(d);
  renderCalendar(d);
  renderResultsSelect(d);
  renderStats(d);
}

function renderOverview(d) {
  const dl = d.drivers[0], d2 = d.drivers[1];
  const cl = d.constructors[0], c2 = d.constructors[1];

  $("#driverLeader").style.setProperty("--accent", teamColor(dl.team));
  $("#driverLeader").innerHTML = `
    <div class="lc-label">Drivers' Championship Leader</div>
    <div class="lc-pts"><b>${fmtPts(dl.points)}</b><span>points</span></div>
    <div class="lc-name">${natFlag(dl.nat)}${esc(dl.name)}</div>
    <div class="lc-team">${esc(dl.team)} · ${dl.wins} win${dl.wins === 1 ? "" : "s"}</div>
    <div class="lc-gap">Lead over ${esc(d2 ? d2.code : "—")}: <b>${d2 ? "+" + fmtPts(dl.points - d2.points) : "—"}</b></div>`;

  $("#constructorLeader").style.setProperty("--accent", teamColor(cl.team));
  $("#constructorLeader").innerHTML = `
    <div class="lc-label">Constructors' Championship Leader</div>
    <div class="lc-pts"><b>${fmtPts(cl.points)}</b><span>points</span></div>
    <div class="lc-name">${esc(cl.team)}</div>
    <div class="lc-team">${cl.wins} win${cl.wins === 1 ? "" : "s"}</div>
    <div class="lc-gap">Lead over ${esc(c2 ? c2.team : "—")}: <b>${c2 ? "+" + fmtPts(cl.points - c2.points) : "—"}</b></div>`;

  const next = d.races.find((r) => r.status === "upcoming" && (!r.date || r.date >= todayISO()));
  const nc = $("#nextRace");
  if (next) {
    const days = Math.max(0, Math.ceil((new Date(next.date) - new Date()) / 864e5));
    nc.innerHTML = `
      <div class="card-title">Next Race</div>
      <div class="nc-flag">${flag(next.country)}</div>
      <div class="nc-round">Round ${next.round}</div>
      <div class="nc-name">${esc(next.name)}</div>
      <div class="nc-sub">${esc(next.locality)} · ${fmtDate(next.date)}</div>
      <div class="nc-countdown"><b>${days}</b> day${days === 1 ? "" : "s"} to go</div>`;
  } else {
    nc.innerHTML = `<div class="card-title">Season</div>
      <div class="nc-name">Season complete</div>
      <div class="nc-sub">All ${d.races.length} rounds finished 🏁</div>`;
  }

  const last = [...d.races].reverse().find((r) => r.status === "completed" && r.podium.length);
  const lc = $("#lastRace");
  if (last) {
    const medals = ["🥇", "🥈", "🥉"];
    lc.innerHTML = `<div class="card-title">Last Race — ${esc(last.name)}</div>` +
      last.podium.map((p, i) => `
        <div class="podium-row">
          <span class="pp">${medals[i] || p.pos}</span>
          <span class="swatch" style="background:${teamColor(p.team)}"></span>
          <span class="pd">${natFlag(p.nat)}${esc(p.name)}</span>
          <span class="pt">${esc(p.team)}</span>
        </div>`).join("");
  } else {
    lc.innerHTML = `<div class="card-title">Last Race</div><div class="nc-sub">No races completed yet.</div>`;
  }

  $("#miniDrivers").innerHTML = miniRows(d.drivers.slice(0, 5), (x) => x.name, (x) => x.team, (x) => x.team, (x) => x.nat);
  $("#miniConstructors").innerHTML = miniRows(d.constructors.slice(0, 5), (x) => x.team, (x) => `${x.wins} win${x.wins === 1 ? "" : "s"}`, (x) => x.team);
}

function miniRows(rows, name, sub, team, natFn) {
  return rows.map((x) => `
    <div class="row">
      <span class="pos">${x.pos}</span>
      <span class="swatch" style="background:${teamColor(team(x))}"></span>
      <span><div class="who">${natFn ? natFlag(natFn(x)) : ""}${esc(name(x))}</div><div class="sub">${esc(sub(x))}</div></span>
      <span class="pts">${fmtPts(x.points)}</span>
    </div>`).join("");
}

function renderStandings(d) {
  const maxD = Math.max(1, ...d.drivers.map((x) => x.points));
  $("#driverStandings").innerHTML = d.drivers.map((x) => standRow(
    x.pos, `${natFlag(x.nat)}${esc(x.name)} <span class="code">${esc(x.code)}</span>`, x.team, x.points, maxD, x.wins)).join("");
  const maxC = Math.max(1, ...d.constructors.map((x) => x.points));
  $("#constructorStandings").innerHTML = d.constructors.map((x) => standRow(
    x.pos, esc(x.team), x.team, x.points, maxC, x.wins)).join("");
}

function standRow(pos, nameHtml, team, points, max, wins) {
  const w = Math.max(2, (points / max) * 100);
  return `
    <div class="st-row">
      <div class="st-pos">${pos}</div>
      <div class="st-main">
        <div class="st-name">${swatch(team)}<span>${nameHtml}</span></div>
        <div class="st-team">${esc(team)}</div>
        <div class="bar"><span style="width:${w}%;background:${teamColor(team)}"></span></div>
      </div>
      <div class="st-pts">${fmtPts(points)}<small>${wins} win${wins === 1 ? "" : "s"}</small></div>
    </div>`;
}

function renderCalendar(d) {
  const done = d.races.filter((r) => r.status === "completed").length;
  const postponed = d.races.filter((r) => r.status === "postponed").length;
  $("#calendarMeta").textContent = `${done} of ${d.races.length - postponed} rounds completed`
    + (postponed ? ` · ${postponed} postponed` : "");
  const today = todayISO();
  const nextRound = (d.races.find((r) => r.status === "upcoming" && (!r.date || r.date >= today)) || {}).round;
  const grid = $("#calendarGrid");
  grid.innerHTML = "";
  d.races.forEach((r) => {
    const isNext = r.round === nextRound;
    const isPostponed = r.status === "postponed";        // scheduled, never held (skipped in f1db)
    const isTBC = r.status === "upcoming" && r.date && r.date < today;  // scheduled, result pending
    const badge = r.status === "completed" ? `<span class="badge done">Completed</span>`
      : isPostponed ? `<span class="badge off">Postponed</span>`
      : isNext ? `<span class="badge next">Next Up</span>`
      : isTBC ? `<span class="badge up">TBC</span>`
      : `<span class="badge up">Upcoming</span>`;
    const foot = r.status === "completed" && r.winner
      ? `<span class="rc-winner">${swatch(r.winner.team, 4, 15)} ${esc(r.winner.code)} · ${esc(r.winner.name.split(" ").slice(-1)[0])}</span>`
      : isPostponed
      ? `<span class="rc-sub">Not held${r.date ? " · was " + fmtDate(r.date) : ""}</span>`
      : `<span class="rc-sub">${fmtDate(r.date)}</span>`;
    const card = el("div", "race-card" + (isNext ? " next" : "") + (isPostponed ? " off" : ""));
    card.innerHTML = `
      <div class="rc-top"><span class="rc-round">R${r.round}</span><span class="rc-flag">${flag(r.country)}</span></div>
      <div class="rc-name">${esc(r.name)}</div>
      <div class="rc-sub">${esc(r.locality)}${r.country ? ", " + esc(r.country) : ""}</div>
      <div class="rc-foot">${badge}${foot}</div>`;
    if (r.status === "completed") {
      card.style.cursor = "pointer";
      card.addEventListener("click", () => { showTab("results"); selectRace(r.round); });
    } else {
      card.style.cursor = "default";
    }
    grid.appendChild(card);
  });
}

function renderResultsSelect(d) {
  const sel = $("#raceSelect");
  const completed = d.races.filter((r) => r.status === "completed");
  sel.innerHTML = completed.map((r) => `<option value="${r.round}">R${r.round} — ${esc(r.name)}</option>`).join("")
    || `<option value="">No completed races</option>`;
  sel.onchange = () => renderRaceDetail(d, +sel.value);
  const last = completed[completed.length - 1];
  if (last) { sel.value = last.round; renderRaceDetail(d, last.round); }
  else $("#raceDetail").innerHTML = `<div class="empty-note">No completed races in this season yet.</div>`;
}

function selectRace(round) {
  const sel = $("#raceSelect");
  sel.value = round;
  renderRaceDetail(data(), round);
}

/* ---------------- season stats (sortable table) ---------------- */
const fmt1 = (v) => (v == null ? "—" : (+v).toFixed(1));
const fmt2 = (v) => (v == null ? "—" : (+v).toFixed(2));
const fmtSigned = (v) => (v == null ? "—" : v > 0 ? "+" + v : String(v));
const gainClass = (v) => (v == null ? "" : v > 0 ? "pos" : v < 0 ? "neg" : "");

// `desc:true` => first click sorts high→low (best-first for a "more is better"
// stat); `desc:false` sorts low→high first (best-first for avg grid/finish, DNFs…).
const STAT_COLS = [
  { key: "points",     label: "Points",     desc: true,  primary: true, fmt: fmtPts, t: "Championship points (includes sprints)" },
  { key: "wins",       label: "Wins",       desc: true,  t: "Grand Prix wins" },
  { key: "podiums",    label: "Podiums",    desc: true,  t: "Top-3 finishes" },
  { key: "poles",      label: "Poles",      desc: true,  t: "Qualifying P1" },
  { key: "starts",     label: "Starts",     desc: true,  t: "Grand Prix starts" },
  { key: "avg_finish", label: "Avg Finish", desc: false, fmt: fmt1, t: "Mean finish position — lower is better" },
  { key: "avg_grid",   label: "Avg Grid",   desc: false, fmt: fmt1, t: "Mean start position — lower is better" },
  { key: "gained",     label: "Places +/−", desc: true,  fmt: fmtSigned, cls: gainClass, t: "Net positions gained, grid → flag (front-runners trend negative)" },
  { key: "avg_stops",  label: "Avg Stops",  desc: false, fmt: fmt1, t: "Average pit stops per race" },
  { key: "stop_s",     label: "Stop (s)",   desc: false, fmt: fmt2, t: "Est. stationary tyre-change time — median, with pit-lane transit removed (public data records only full pit-lane time) — lower is better" },
  { key: "pts_fin",    label: "Pts Fin",    desc: true,  t: "Points finishes (top 10)" },
  { key: "dnf",        label: "DNF",        desc: false, t: "Did not finish" },
  { key: "dotd",       label: "DOTD",       desc: true,  t: "Driver of the Day awards" },
];

let statsSort = { key: "points", dir: "desc" };

function renderStats(d) {
  const stats = d.stats || [];
  const done = d.races.filter((r) => r.status === "completed").length;
  const box = $("#statsTable"), note = $("#statsNote");
  $("#statsMeta").textContent = stats.length ? `${stats.length} drivers · ${done} rounds` : "";
  if (!stats.length) {
    note.textContent = "";
    box.innerHTML = `<div class="empty-note">No completed races in this season yet.</div>`;
    return;
  }
  const hasLed = stats.some((s) => s.laps_led != null);
  const cols = STAT_COLS.slice();
  if (hasLed) cols.push({ key: "laps_led", label: "Laps Led", desc: true, t: "Laps led" });
  if (!cols.some((c) => c.key === statsSort.key)) statsSort = { key: "points", dir: "desc" };
  note.innerHTML =
    `Every completed round, aggregated. Wins · podiums · poles are Grand&nbsp;Prix figures; ` +
    `<b>Points</b> is the championship total. <b>Places&nbsp;+/−</b> is net positions gained from grid to flag ` +
    `(front-runners naturally trend negative). <b>Stop&nbsp;(s)</b> estimates the stationary tyre-change time — ` +
    `the circuit's pit-lane transit is removed from the public data, which records only full pit-lane time. ` +
    `Click any column to sort.` +
    (hasLed ? "" : ` <span class="muted">Laps-led needs lap-by-lap timing — not in the public dataset — so it shows only after a timing-enabled fetch.</span>`);
  drawStats(box, stats, cols);
}

function sortStats(stats, { key, dir }) {
  const sign = dir === "desc" ? -1 : 1;
  return stats.slice().sort((a, b) => {
    const av = a[key], bv = b[key];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;            // nulls always sort last
    if (bv == null) return -1;
    return av < bv ? -sign : av > bv ? sign : 0;
  });
}

function drawStats(box, stats, cols) {
  const sorted = sortStats(stats, statsSort);
  const head = `<th class="stx-rank">#</th><th class="stx-drv">Driver</th><th class="stx-team">Team</th>` +
    cols.map((c) => {
      const on = statsSort.key === c.key;
      return `<th class="num sortable${on ? " sorted " + statsSort.dir : ""}${c.primary ? " primary" : ""}" ` +
        `data-key="${c.key}" title="${esc(c.t || c.label)}">${esc(c.label)}</th>`;
    }).join("");
  const body = sorted.map((s, i) => {
    const cells = cols.map((c) => {
      const v = s[c.key];
      const disp = c.fmt ? c.fmt(v) : (v == null ? "—" : v);
      const cls = (c.cls ? c.cls(v) : "") + (c.primary ? " primary" : "") + (statsSort.key === c.key ? " on" : "");
      return `<td class="num ${cls.trim()}">${disp}</td>`;
    }).join("");
    return `<tr style="--accent:${teamColor(s.team)}">
      <td class="stx-rank">${i + 1}</td>
      <td class="stx-drv"><span class="cell-driver">${swatch(s.team)}${natFlag(s.nat)}<span>${esc(s.name)}</span><span class="code">${esc(s.code)}</span></span></td>
      <td class="stx-team">${esc(s.team)}</td>${cells}</tr>`;
  }).join("");
  box.innerHTML = `<div class="stats-scroll"><table class="stats-table">
    <thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
  box.querySelectorAll("th.sortable").forEach((th) =>
    th.addEventListener("click", () => {
      const k = th.dataset.key;
      if (statsSort.key === k) statsSort.dir = statsSort.dir === "desc" ? "asc" : "desc";
      else statsSort = { key: k, dir: cols.find((c) => c.key === k).desc ? "desc" : "asc" };
      drawStats(box, stats, cols);
    }));
}

/* ---------------- race progression (interactive lap scrubber) ---------------- */
const SVGNS = "http://www.w3.org/2000/svg";
let _progTimer = null;

function stopProgression() {
  if (_progTimer) { clearInterval(_progTimer); _progTimer = null; }
}

function _svg(tag, attrs) {
  const n = document.createElementNS(SVGNS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  return n;
}

// Per-driver position for every lap. Uses real lap-by-lap telemetry when the
// data carries it (race.laps from the CI fetch); otherwise derives an honest
// progression from each driver's REAL grid, finishing position and laps run.
function deriveLapPositions(race) {
  const results = race.results || [];
  const n = results.length || 20;
  if (race.laps && typeof race.laps === "object") {
    const total = race.total_laps || Math.max(1, ...Object.values(race.laps).map((a) => a.length));
    const teamOf = {}; results.forEach((r) => (teamOf[r.code] = r.team));
    const drivers = Object.keys(race.laps).map((code) => ({
      code, team: teamOf[code] || "", positions: race.laps[code],
      fin: race.laps[code][race.laps[code].length - 1] || n,
    }));
    return { total, n, drivers, real: true };
  }
  const total = race.total_laps || Math.max(1, ...results.map((r) => r.laps || 1));
  const classified = results.filter((r) => r.pos != null).slice().sort((a, b) => a.pos - b.pos);
  const dnf = results.filter((r) => r.pos == null).slice().sort((a, b) => (b.laps || 0) - (a.laps || 0));
  const finalPos = {};
  classified.forEach((r) => (finalPos[r.code] = r.pos));
  dnf.forEach((r, i) => (finalPos[r.code] = classified.length + i + 1));

  // The last lap a car appears on the chart. A CLASSIFIED finisher runs to the
  // flag even if lapped (so it holds its finishing slot at the end); a RETIREMENT
  // drops out at the lap it reached. Retirements with no recorded lap count are
  // staggered through the race so they visibly retire instead of being ranked
  // among the finishers on the final lap (which is what "laps || total" did).
  const dnfOrder = dnf.map((r) => r.code);
  const lastLap = (r) => {
    if (r.pos != null) return total;                          // classified → to the flag
    const laps = Number.isInteger(r.laps) && r.laps > 0 ? r.laps : 0;
    if (laps) return Math.min(laps, total - 1);               // known retirement lap
    const k = dnfOrder.indexOf(r.code), m = Math.max(1, dnfOrder.length - 1);
    return Math.max(1, Math.min(total - 1, Math.round(total * (0.8 - 0.45 * (k / m)))));
  };
  const curve = results.map((r) => {
    const fin = finalPos[r.code] || n;
    return {
      code: r.code, team: r.team, fin,
      grid: r.grid && r.grid > 0 ? r.grid : fin,
      last: lastLap(r),
    };
  });

  // Positions are a classification: at any lap they must be UNIQUE (1..k across
  // the cars still running). Rounding each driver's interpolated value on its own
  // let two cars land on the same slot — instead, rank the running cars by their
  // continuous value each lap and hand out distinct places.
  const pos = {};
  curve.forEach((c) => (pos[c.code] = []));
  for (let lap = 1; lap <= total; lap++) {
    const running = [];
    for (const c of curve) {
      if (lap > c.last) { pos[c.code].push(null); continue; }
      const t = c.last <= 1 ? 1 : (lap - 1) / (c.last - 1);
      running.push({ code: c.code, v: c.grid + (c.fin - c.grid) * (t * t * (3 - 2 * t)), fin: c.fin, grid: c.grid });
    }
    running.sort((a, b) => a.v - b.v || a.fin - b.fin || a.grid - b.grid || (a.code < b.code ? -1 : 1));
    running.forEach((d, i) => pos[d.code].push(i + 1));
  }

  const drivers = curve.map((c) => ({ code: c.code, team: c.team, positions: pos[c.code], fin: c.fin }));
  drivers.sort((a, b) => a.fin - b.fin);
  return { total, n, drivers, real: false };
}

function buildProgression(race) {
  const { total, n, drivers, real } = deriveLapPositions(race);
  const W = 1000, H = 440, padL = 44, padR = 48, padT = 16, padB = 30;
  const plotW = W - padL - padR, plotH = H - padT - padB;
  const xOf = (lap) => padL + (total <= 1 ? 0 : ((lap - 1) / (total - 1)) * plotW);
  const yOf = (pos) => padT + (n <= 1 ? 0 : ((pos - 1) / (n - 1)) * plotH);

  const wrap = el("div", "progression");
  wrap.innerHTML = `<div class="prog-head"><span class="card-title">Race Progression</span>
    <span class="prog-note">${real ? "lap-by-lap" : "grid → finish (approx)"} · drag or play to scrub</span></div>`;

  const s = _svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "prog-svg", preserveAspectRatio: "xMidYMid meet" });
  for (let p = 1; p <= n; p++) {
    if (p === 1 || p % 5 === 0) {
      s.appendChild(_svg("line", { x1: padL, y1: yOf(p), x2: W - padR, y2: yOf(p), class: "prog-grid" }));
      const t = _svg("text", { x: padL - 8, y: yOf(p) + 3.5, class: "prog-axis", "text-anchor": "end" });
      t.textContent = "P" + p; s.appendChild(t);
    }
  }
  const step = total <= 30 ? 5 : 10;
  for (let lap = 1; lap <= total; lap += lap === 1 ? step - 1 : step) {
    const t = _svg("text", { x: xOf(lap), y: H - padB + 18, class: "prog-axis", "text-anchor": "middle" });
    t.textContent = lap; s.appendChild(t);
  }
  const bright = {}, marker = {}, label = {};
  drivers.forEach((d) => {
    const color = teamColor(d.team);
    const pts = d.positions.map((p, i) => (p == null ? null : `${xOf(i + 1)},${yOf(p)}`)).filter(Boolean);
    s.appendChild(_svg("polyline", { points: pts.join(" "), class: "prog-faint", stroke: color }));
    bright[d.code] = _svg("polyline", { points: "", class: "prog-line", stroke: color });
    s.appendChild(bright[d.code]);
  });
  const vline = _svg("line", { x1: xOf(1), y1: padT, x2: xOf(1), y2: H - padB, class: "prog-vline" });
  s.appendChild(vline);
  drivers.forEach((d) => {
    const color = teamColor(d.team);
    marker[d.code] = _svg("circle", { r: 3.4, class: "prog-dot", fill: color, cx: -20, cy: -20 });
    s.appendChild(marker[d.code]);
    const lab = _svg("text", { class: "prog-code", x: -20, y: -20, fill: color });
    lab.textContent = d.code; label[d.code] = lab; s.appendChild(lab);
  });
  wrap.appendChild(s);

  const ctrl = el("div", "prog-controls");
  ctrl.innerHTML = `<button type="button" class="prog-play">Play</button>
    <input type="range" class="prog-slider" min="1" max="${total}" value="${total}" step="1" aria-label="Lap">
    <span class="prog-lap">Lap <input type="number" class="prog-num" min="1" max="${total}" value="${total}" aria-label="Pick lap"> / ${total}</span>`;
  wrap.appendChild(ctrl);
  const playBtn = $(".prog-play", ctrl), slider = $(".prog-slider", ctrl), num = $(".prog-num", ctrl);

  function setLap(L) {
    L = Math.max(1, Math.min(total, L | 0));
    vline.setAttribute("x1", xOf(L)); vline.setAttribute("x2", xOf(L));
    slider.value = L;
    if (document.activeElement !== num) num.value = L;   // don't clobber while typing
    drivers.forEach((d) => {
      const pts = [];
      for (let lap = 1; lap <= L; lap++) { const p = d.positions[lap - 1]; if (p != null) pts.push(`${xOf(lap)},${yOf(p)}`); }
      bright[d.code].setAttribute("points", pts.join(" "));
      const cur = d.positions[L - 1];
      const on = cur != null ? "1" : "0";
      marker[d.code].style.opacity = on; label[d.code].style.opacity = on;
      if (cur != null) {
        marker[d.code].setAttribute("cx", xOf(L)); marker[d.code].setAttribute("cy", yOf(cur));
        label[d.code].setAttribute("x", xOf(L) + 6); label[d.code].setAttribute("y", yOf(cur) + 3.5);
      }
    });
  }
  function stopPlay() { stopProgression(); playBtn.textContent = "Play"; }
  function play() {
    stopProgression();
    let L = +slider.value >= total ? 1 : +slider.value;
    playBtn.textContent = "Pause";
    _progTimer = setInterval(() => {
      L += 1;
      if (L > total) { slider.value = total; setLap(total); stopPlay(); return; }
      slider.value = L; setLap(L);
    }, 110);
  }
  slider.addEventListener("input", () => { stopPlay(); setLap(+slider.value); });
  num.addEventListener("change", () => { stopPlay(); setLap(+num.value || 1); });
  num.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { stopPlay(); setLap(+num.value || 1); num.blur(); }
  });
  playBtn.addEventListener("click", () => (_progTimer ? stopPlay() : play()));

  setLap(total);
  return wrap;
}

// Rendered replay video (optional). Shown only if a video exists for the race —
// either inlined for the self-contained bundle (window.RACE_VIDEOS) or served
// from media/<season>-<round>.mp4 on the deployed site. Hidden gracefully if not.
function mountReplay(race) {
  const key = `${current}-${race.round}`;
  const embedded = window.RACE_VIDEOS && window.RACE_VIDEOS[key];
  const wrap = el("div", "replay");
  wrap.style.display = "none";
  wrap.innerHTML = `<div class="prog-head"><span class="card-title">Race Replay</span>
    <span class="prog-note">${embedded ? "sample render" : "rendered animation"}</span></div>`;
  const v = document.createElement("video");
  v.className = "replay-video";
  v.controls = true;
  v.preload = embedded ? "auto" : "metadata";
  v.playsInline = true;
  v.src = embedded || `media/${key}.mp4`;
  v.addEventListener("loadedmetadata", () => { wrap.style.display = ""; });
  v.addEventListener("error", () => wrap.remove());
  wrap.appendChild(v);
  $("#raceDetail").appendChild(wrap);
}

function renderRaceDetail(d, round) {
  stopProgression();
  const r = d.races.find((x) => x.round === round);
  const box = $("#raceDetail");
  if (!r || !r.results.length) { box.innerHTML = `<div class="empty-note">No results available.</div>`; return; }
  const medals = ["🥇", "🥈", "🥉"];
  const podium = r.podium.map((p, i) => `
    <div class="pod" style="--accent:${teamColor(p.team)}">
      <div class="medal">${medals[i]}</div>
      <div class="pn">${natFlag(p.nat)}${esc(p.name)}</div>
      <div class="pt">${esc(p.team)}</div>
    </div>`).join("");
  const rows = r.results.map((x) => `
    <tr>
      <td class="num">${x.status === "Finished" || x.pos ? x.pos : "—"}</td>
      <td><span class="cell-driver">${swatch(x.team)}${natFlag(x.nat)}<span>${esc(x.name)}</span><span class="code">${esc(x.code)}</span></span></td>
      <td>${esc(x.team)}</td>
      <td class="num">${x.grid ?? "—"}</td>
      <td class="num">${x.status === "Finished" ? "" : `<span class="dnf">${esc(x.status)}</span>`}${x.status === "Finished" ? x.laps ?? "" : ""}</td>
      <td class="num">${x.points ? fmtPts(x.points) : "—"}</td>
    </tr>`).join("");
  box.innerHTML = `
    <div class="race-hero">
      <div class="card" style="flex:1 1 100%">
        <div class="card-title">${flag(r.country)} ${esc(r.name)} · Round ${r.round} · ${fmtDate(r.date)}</div>
        <div class="podium-cards">${podium}</div>
        ${r.fastest_lap ? `<div style="margin-top:14px;color:var(--ink-2);font-size:13px">⏱ Fastest lap — <b style="color:var(--ink)">${esc(r.fastest_lap.name || r.fastest_lap.code)}</b> ${esc(r.fastest_lap.time || "")}</div>` : ""}
      </div>
    </div>
    <table class="results">
      <thead><tr><th class="num">Pos</th><th>Driver</th><th>Team</th><th class="num">Grid</th><th class="num">Laps / Status</th><th class="num">Pts</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  box.insertBefore(buildProgression(r), box.querySelector("table.results"));
  mountReplay(r);
}

/* ---------------- helpers & wiring ---------------- */
function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function fmtDate(s) {
  if (!s) return "TBC";
  const d = new Date(s + "T00:00:00");
  return isNaN(d) ? s : d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function showTab(name) {
  if (name !== "results") stopProgression();
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === name));
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setSeason(year) {
  if (!SEASONS[year]) return;
  current = year;
  document.querySelectorAll("#seasonToggle button").forEach((b) => b.classList.toggle("active", b.dataset.season === year));
  render();
}

function wire() {
  document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
  document.querySelectorAll("#seasonToggle button").forEach((b) => b.addEventListener("click", () => setSeason(b.dataset.season)));
}

async function boot() {
  wire();
  const years = ["2022", "2023", "2024", "2025", "2026"];
  // Embedded mode (self-contained bundle): data injected as window.SEASON_DATA.
  if (window.SEASON_DATA) {
    Object.assign(SEASONS, window.SEASON_DATA);
  } else {
    await Promise.all(years.map(async (y) => {
      try {
        const res = await fetch(`data/${y}.json`, { cache: "no-store" });
        if (res.ok) SEASONS[y] = await res.json();
      } catch (e) { /* offline / file:// */ }
    }));
  }
  const avail = years.filter((y) => SEASONS[y]);
  if (!avail.length) {
    $("#main").innerHTML = `<div class="empty-note">Could not load season data. Serve this folder over HTTP (e.g. <code>python -m http.server</code>) or run the deploy workflow.</div>`;
    return;
  }
  if (!SEASONS[current]) current = avail[avail.length - 1];
  const src = (SEASONS[current] || {}).source || "f1db + fastf1";
  $("#footNote").textContent = "Data via " + src;
  setSeason(current);
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();
