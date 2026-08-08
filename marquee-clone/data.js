/* ===========================================================================
   Touchline (Marquee-concept study clone) — synthetic data layer.
   Every player, club and number here is fictional, generated from a seeded
   PRNG so the demo is deterministic across reloads. No real-world player data.
   =========================================================================== */
"use strict";

const TL = window.TL = window.TL || {};

/* ---- seeded PRNG (mulberry32) so the "database" is stable ---- */
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = mulberry32(20260808);
const ri = (a, b) => a + Math.floor(rnd() * (b - a + 1));
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

/* ---- name & club pools (invented) ---- */
const FIRST = ["Mateo","Ilias","Jorren","Kwame","Dario","Emeka","Luca","Rasmus","Thiemo","Yann",
  "Bruno","Santi","Aleix","Nikola","Petar","Timo","Joaquin","Ederson","Kaito","Min-jun",
  "Ousmane","Sefu","Tarik","Iker","Lorenz","Milan","Andrej","Casper","Felipe","Gustav",
  "Haruki","Ibrahima","Jonas","Kenan","Leandro","Mahmoud","Nathan","Oriol","Pavel","Quincy",
  "Renato","Samuel","Teun","Umar","Viktor","Wesley","Xavi","Yusuf","Zeki","Anton"];
const LAST = ["Verhagen","Okafor","Lindqvist","Marchetti","Dubois","Kovacevic","Alarcon","Petrov","Sarr","Nystrom",
  "Cardoso","Ferreyra","Bakker","Jansson","Moreau","Castellanos","Diallo","Vasquez","Tanaka","Novak",
  "Reinders","Bergstrom","Costa","Mensah","Ricci","Weiss","Horvat","Aoki","Njoku","Falk",
  "Guzman","Sorescu","Toure","Vidal","Wozniak","Yilmaz","Zamora","Brandt","Cisse","Delgado",
  "Eriksen-Voss","Fontaine","Grbic","Holm","Iversen","Jimenez","Keita","Larsen","Mbaye","Oduya"];
const CLUBS = [
  ["FC Meridian", "Eredivisie", "NED"], ["Atletico Sur", "LaLiga 2", "ESP"],
  ["Union Nordhaven", "Superliga", "DEN"], ["Sporting Aurora", "Liga Portugal", "POR"],
  ["Dynamo Vardar", "HNL", "CRO"], ["Rapid Ostmark", "Bundesliga 2", "GER"],
  ["Athletic Rivera", "Primera Nacional", "ARG"], ["Olympique Corsaire", "Ligue 2", "FRA"],
  ["Vale United", "Championship", "ENG"], ["Calcio Adriatico", "Serie B", "ITA"],
  ["Zenith Karpaty", "Ekstraklasa", "POL"], ["Kobe Harbor FC", "J1 League", "JPN"],
  ["River Delta SC", "MLS", "USA"], ["Austria Donau", "Bundesliga (AUT)", "AUT"],
  ["Brann Fjord", "Eliteserien", "NOR"], ["Gallia Turin", "Serie A", "ITA"],
  ["Real Estrella", "LaLiga", "ESP"], ["Northgate Rovers", "Premier League", "ENG"],
  ["Palmeiras do Norte", "Serie A (BRA)", "BRA"], ["Ajax Zuidoost", "Eredivisie", "NED"]];
const NATIONS = ["Netherlands","Nigeria","Sweden","Italy","France","Croatia","Spain","Bulgaria","Senegal","Norway",
  "Portugal","Argentina","Denmark","Ghana","Japan","Serbia","Germany","Turkey","Brazil","USA","Mali","South Korea"];

/* positions with attribute archetypes: [key, label, line] */
const POSITIONS = [
  ["GK", "Goalkeeper", "GK"], ["CB", "Centre-back", "DEF"], ["FB", "Full-back", "DEF"],
  ["DM", "Defensive midfielder", "MID"], ["CM", "Central midfielder", "MID"],
  ["AM", "Attacking midfielder", "MID"], ["WG", "Winger", "ATT"], ["ST", "Striker", "ATT"]];

/* per-position attribute centres (0-100) */
const ARCH = {
  GK: { pace: 42, stamina: 55, strength: 70, control: 55, dribbling: 35, passing: 62, vision: 55, finishing: 12, aerial: 74, defending: 80, pressing: 30, positioning: 84, composure: 76 },
  CB: { pace: 58, stamina: 66, strength: 80, control: 58, dribbling: 42, passing: 64, vision: 55, finishing: 25, aerial: 82, defending: 84, pressing: 60, positioning: 80, composure: 72 },
  FB: { pace: 78, stamina: 82, strength: 62, control: 68, dribbling: 66, passing: 68, vision: 60, finishing: 35, aerial: 55, defending: 72, pressing: 72, positioning: 68, composure: 64 },
  DM: { pace: 60, stamina: 80, strength: 74, control: 70, dribbling: 55, passing: 76, vision: 70, finishing: 30, aerial: 66, defending: 78, pressing: 76, positioning: 78, composure: 74 },
  CM: { pace: 66, stamina: 82, strength: 64, control: 76, dribbling: 68, passing: 80, vision: 76, finishing: 48, aerial: 52, defending: 62, pressing: 72, positioning: 70, composure: 72 },
  AM: { pace: 70, stamina: 70, strength: 54, control: 84, dribbling: 80, passing: 82, vision: 84, finishing: 66, aerial: 40, defending: 40, pressing: 58, positioning: 66, composure: 74 },
  WG: { pace: 86, stamina: 74, strength: 52, control: 82, dribbling: 84, passing: 70, vision: 66, finishing: 66, aerial: 38, defending: 38, pressing: 62, positioning: 62, composure: 64 },
  ST: { pace: 78, stamina: 70, strength: 72, control: 76, dribbling: 68, passing: 60, vision: 58, finishing: 84, aerial: 68, defending: 25, pressing: 60, positioning: 82, composure: 76 }
};
const HEIGHT_BASE = { GK: 190, CB: 188, FB: 178, DM: 183, CM: 180, AM: 176, WG: 175, ST: 184 };

const ATTR_KEYS = Object.keys(ARCH.CM);

function makePlayer(id, fixedPos) {
  const [pos, posLabel, line] = fixedPos || pick(POSITIONS);
  const base = ARCH[pos];
  const quality = rnd();                       // overall talent tier 0..1
  const attrs = {};
  for (const k of ATTR_KEYS) {
    attrs[k] = clamp(Math.round(base[k] + (quality - 0.45) * 28 + (rnd() - 0.5) * 16), 20, 97);
  }
  const age = ri(17, 33);
  const height = clamp(HEIGHT_BASE[pos] + ri(-7, 8), 168, 202);
  const club = pick(CLUBS);
  // value: quality + age curve, in €m
  const ageFactor = age <= 23 ? 1.25 : age <= 27 ? 1.1 : age <= 30 ? 0.75 : 0.4;
  const value = Math.max(0.4, +(Math.pow(quality + 0.25, 3) * 38 * ageFactor * (0.7 + rnd() * 0.6)).toFixed(1));
  const styles = [];
  if (attrs.pressing >= 70) styles.push("high-press");
  if (attrs.passing >= 76 && attrs.control >= 72) styles.push("possession");
  if (attrs.pace >= 82) styles.push("transition");
  if (attrs.aerial >= 74) styles.push("aerial");
  if (attrs.vision >= 78) styles.push("creator");
  if (styles.length === 0) styles.push("balanced");
  return {
    id, name: `${pick(FIRST)} ${pick(LAST)}`,
    pos, posLabel, line,
    age, height, foot: rnd() < 0.24 ? "Left" : (rnd() < 0.08 ? "Both" : "Right"),
    nation: pick(NATIONS), club: club[0], league: club[1], country: club[2],
    value, wageK: Math.round(value * ri(6, 14)),          // €k / week
    contractUntil: ri(2026, 2030),
    minutesPct: ri(28, 98),                               // % of available league minutes
    formTrend: +(rnd() * 2 - 0.8).toFixed(2),             // z-score-ish last-8 trend
    injuryDays: ri(0, 120),                               // days missed, last 2 seasons
    attrs, styles, quality
  };
}

/* ---- the database: 120 scoutable players ---- */
TL.players = [];
(function () {
  let id = 1;
  for (const p of POSITIONS) {                 // guarantee coverage per position
    for (let i = 0; i < (p[0] === "GK" ? 8 : 16); i++) TL.players.push(makePlayer(id++, p));
  }
})();

/* ---- "your club": DNA + current squad, used for synergy & fit ---- */
TL.club = {
  name: "Harbor City FC",
  league: "Premier League",
  style: "high-press",       // user can switch: high-press | possession | transition
  budgetM: 30,
  squad: []
};
(function () {
  const wanted = ["GK","GK","CB","CB","CB","FB","FB","DM","CM","CM","AM","WG","WG","ST","ST"];
  let id = 1000;
  for (const pos of wanted) {
    const p = makePlayer(id++, POSITIONS.find(x => x[0] === pos));
    p.club = TL.club.name; p.league = TL.club.league; p.country = "ENG";
    TL.club.squad.push(p);
  }
})();

/* attribute display labels */
TL.ATTR_LABELS = {
  pace: "Pace", stamina: "Stamina", strength: "Strength", control: "Ball control",
  dribbling: "Dribbling", passing: "Passing", vision: "Vision", finishing: "Finishing",
  aerial: "Aerial", defending: "Defending", pressing: "Pressing",
  positioning: "Positioning", composure: "Composure"
};
TL.ATTR_KEYS = ATTR_KEYS;
