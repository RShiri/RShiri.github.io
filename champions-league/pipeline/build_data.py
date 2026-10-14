"""Build champions-league/data/ucl.json from the raw result files.

Sources
  data/raw/cl_<season>.txt   openfootball/champions-league (CC0), football.txt format.
  data/raw/cl_<season>.csv   hand-entered results for a season openfootball has not
                             published yet (the current one). A .txt for the same season
                             wins over the .csv, so dropping in openfootball's file later
                             replaces the manual entries.

Run:  python champions-league/pipeline/build_data.py
No third-party packages. The dashboard reads only the JSON this writes.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "ucl.json"

SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26", "2026-27"]
FORMAT = {s: ("groups" if s in ("2022-23", "2023-24") else "league") for s in SEASONS}

# One display name per club across seasons (openfootball spells some clubs two ways).
ALIAS = {
    "1. FC Union Berlin": "Union Berlin", "AC Sparta Praha": "Sparta Praha", "AFC Ajax": "Ajax",
    "AS Monaco FC": "Monaco", "Arsenal FC": "Arsenal", "Aston Villa FC": "Aston Villa", "Atalanta BC": "Atalanta",
    "Atlético Madrid": "Atlético Madrid", "Club Atlético de Madrid": "Atlético Madrid",
    "BSC Young Boys": "Young Boys", "Bayer 04 Leverkusen": "Leverkusen", "Bayer Leverkusen": "Leverkusen",
    "Bayern München": "Bayern München", "FC Bayern München": "Bayern München", "Bologna FC 1909": "Bologna",
    "Celtic FC": "Celtic", "Chelsea FC": "Chelsea", "Club Brugge KV": "Club Brugge",
    "Dinamo Zagreb": "Dinamo Zagreb", "GNK Dinamo Zagreb": "Dinamo Zagreb", "FC Barcelona": "Barcelona",
    "FC Internazionale Milano": "Inter", "FC Porto": "Porto", "FC Red Bull Salzburg": "Salzburg",
    "RB Salzburg": "Salzburg", "FK Bodø/Glimt": "Bodø/Glimt", "FK Crvena Zvezda": "Crvena Zvezda",
    "FK Kairat": "Kairat", "FK Shakhtar Donetsk": "Shakhtar Donetsk", "Feyenoord Rotterdam": "Feyenoord",
    "Galatasaray SK": "Galatasaray", "Girona FC": "Girona", "Juventus FC": "Juventus", "Lille OSC": "Lille",
    "Liverpool FC": "Liverpool", "Manchester City FC": "Manchester City", "Manchester United FC": "Manchester United",
    "Newcastle United FC": "Newcastle", "Olympique Marseille": "Marseille", "Olympique de Marseille": "Marseille",
    "PAE Olympiakos SFP": "Olympiacos", "Paphos FC": "Paphos", "Paris Saint-Germain FC": "Paris Saint-Germain",
    "Qarabağ Ağdam FK": "Qarabağ", "Racing Club de Lens": "Lens", "Rangers FC": "Rangers",
    "Real Madrid CF": "Real Madrid", "Real Sociedad de Fútbol": "Real Sociedad", "Royal Antwerp FC": "Antwerp",
    "Royale Union Saint-Gilloise": "Union SG", "SK Slavia Praha": "Slavia Praha", "SK Sturm Graz": "Sturm Graz",
    "SL Benfica": "Benfica", "Sport Lisboa e Benfica": "Benfica", "SS Lazio": "Lazio", "SSC Napoli": "Napoli",
    "Sevilla FC": "Sevilla", "Sporting CP": "Sporting CP", "Sporting Clube de Portugal": "Sporting CP",
    "Sporting Clube de Braga": "Braga", "Stade Brestois 29": "Brest", "Tottenham Hotspur": "Tottenham",
    "Tottenham Hotspur FC": "Tottenham", "Villarreal CF": "Villarreal", "ŠK Slovan Bratislava": "Slovan Bratislava",
    "Viktoria Plzeň": "Viktoria Plzeň", "Maccabi Haifa": "Maccabi Haifa", "FC København": "København",
}

MONTHS = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
DATE_RE = re.compile(r"^\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\w{3}) (\d{1,2})(?: (\d{4}))?\s*$")
MATCH_RE = re.compile(r"^\s+(?:(\d\d:\d\d)\s+)?(.+?) \(([A-Z]{3})\)\s+v\s+(.+?) \(([A-Z]{3})\)\s+(.+?)\s*$")
# 2023-24 lists group games by matchday, so groups are rebuilt from who played whom;
# one club per group pins UEFA's letter.
GROUP_SEEDS = {"2023-24": {"Bayern München": "A", "Arsenal": "B", "Real Madrid": "C", "Inter": "D",
                           "Atlético Madrid": "E", "Borussia Dortmund": "F", "Manchester City": "G", "Barcelona": "H"}}
KO_STAGES = {"round of 16": "R16", "quarterfinals": "QF", "semifinals": "SF", "final": "F"}


def club(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    return ALIAS.get(name, name)


def parse_score(s: str) -> dict:
    """'2-1 (1-1)' | '0-0' | '3-2 a.e.t. (3-0, 1-0)' | '4-3 pen. 1-1 a.e.t. (1-1, 0-1)'."""
    out = {"et": False, "pens": None}
    m = re.match(r"(\d+)-(\d+) pen\. (\d+)-(\d+) a\.e\.t\.", s)
    if m:
        out.update(hg=int(m[3]), ag=int(m[4]), et=True, pens=[int(m[1]), int(m[2])])
        return out
    m = re.match(r"(\d+)-(\d+)( a\.e\.t\.)?", s)
    if not m:
        raise ValueError(f"unreadable score: {s!r}")
    out.update(hg=int(m[1]), ag=int(m[2]), et=bool(m[3]))
    return out


def stage_of(header: str):
    """Section header -> (phase, group letter or None, matchday or None, ko round or None)."""
    h = header.lower()
    g = re.match(r"(?:group|gruppe) ([a-h])$", h)
    if g:
        return "first", g[1].upper(), None, None
    md = re.search(r"matchday (\d+)", h)
    if h.startswith(("group", "league")):
        return "first", None, int(md[1]) if md else None, None
    if h.startswith("playoffs"):
        return "playoff", None, int(md[1]) if md else None, "PO"
    ko = KO_STAGES.get(h.replace("finals, ", "", 1) if h != "final" else h)
    if ko:
        return "ko", None, None, ko
    raise ValueError(f"unknown section: {header!r}")


def parse_txt(path: Path, season: str) -> tuple[list, dict]:
    start_year = int(season[:4])
    matches, countries = [], {}
    phase = group = matchday = rnd = None
    cur = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("▪"):
            phase, group, matchday, rnd = stage_of(line[1:].strip())
            continue
        d = DATE_RE.match(line)
        if d:
            mon, day = MONTHS[d[1]], int(d[2])
            year = int(d[3]) if d[3] else (start_year if mon >= 7 else start_year + 1)
            cur = date(year, mon, day)
            continue
        m = MATCH_RE.match(line)
        if not m:
            continue
        home, away = club(m[2]), club(m[4])
        countries[home], countries[away] = m[3], m[5]
        rec = {"date": cur.isoformat(), "phase": phase, "home": home, "away": away}
        if group:
            rec["group"] = group
        if matchday:
            rec["md"] = matchday
        if rnd:
            rec["round"] = rnd
        rec.update(parse_score(m[6]))
        matches.append(rec)
    return matches, countries


def parse_csv(path: Path) -> tuple[list, dict]:
    """date,phase,md,home,home_cc,away,away_cc,hg,ag  (hg/ag blank = not played yet)."""
    matches, countries = [], {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            home, away = club(r["home"]), club(r["away"])
            countries[home], countries[away] = r["home_cc"], r["away_cc"]
            rec = {"date": r["date"], "phase": r["phase"], "home": home, "away": away, "md": int(r["md"])}
            if r["hg"].strip() == "":
                rec["status"] = "scheduled"
            else:
                rec.update(hg=int(r["hg"]), ag=int(r["ag"]), et=False, pens=None)
            matches.append(rec)
    return matches, countries


def assign_groups(matches: list, seeds: dict) -> None:
    """Recover the eight groups of four from the fixtures when the file has no group headers."""
    first = [m for m in matches if m["phase"] == "first"]
    if not first or all("group" in m for m in first):
        return
    adj: dict[str, set] = {}
    for m in first:
        adj.setdefault(m["home"], set()).add(m["away"])
        adj.setdefault(m["away"], set()).add(m["home"])
    seen, comps = set(), []
    for t in adj:
        if t in seen:
            continue
        stack, comp = [t], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            stack.extend(adj[x] - seen)
        comps.append(comp)
    assert all(len(c) == 4 for c in comps) and len(comps) == 8, "group recovery failed"
    letter = {}
    for c in comps:
        seed = [seeds[t] for t in c if t in seeds]
        assert len(seed) == 1, f"no single seed for group {c}"
        letter.update({t: seed[0] for t in c})
    for m in first:
        m["group"] = letter[m["home"]]


def table(matches: list, teams: list, tiebreak_h2h: bool) -> list:
    rows = {t: dict(team=t, p=0, w=0, d=0, l=0, gf=0, ga=0, agf=0, aw=0, pts=0) for t in teams}
    played = [m for m in matches if "hg" in m]
    for m in played:
        h, a = rows[m["home"]], rows[m["away"]]
        h["p"] += 1; a["p"] += 1
        h["gf"] += m["hg"]; h["ga"] += m["ag"]; a["gf"] += m["ag"]; a["ga"] += m["hg"]; a["agf"] += m["ag"]
        if m["hg"] > m["ag"]:
            h["w"] += 1; a["l"] += 1; h["pts"] += 3
        elif m["hg"] < m["ag"]:
            a["w"] += 1; h["l"] += 1; a["pts"] += 3; a["aw"] += 1
        else:
            h["d"] += 1; a["d"] += 1; h["pts"] += 1; a["pts"] += 1
    for r in rows.values():
        r["gd"] = r["gf"] - r["ga"]

    def h2h_key(group_teams):
        sub = [m for m in played if m["home"] in group_teams and m["away"] in group_teams]
        mini = {r["team"]: r for r in table(sub, group_teams, False)} if sub else {}
        return lambda t: (mini[t]["pts"], mini[t]["gd"], mini[t]["gf"]) if t in mini else (0, 0, 0)

    out = sorted(rows.values(), key=lambda r: (-r["pts"], -r["gd"], -r["gf"], -r["agf"], -r["w"], -r["aw"], r["team"]))
    if tiebreak_h2h:  # old group stage: head-to-head first among teams level on points
        by_pts: dict[int, list] = {}
        for r in out:
            by_pts.setdefault(r["pts"], []).append(r["team"])
        final = []
        for pts in sorted(by_pts, reverse=True):
            tied = by_pts[pts]
            k = h2h_key(tied) if len(tied) > 1 else (lambda t: (0, 0, 0))
            final += sorted((rows[t] for t in tied), key=lambda r: tuple(-x for x in k(r["team"])) + (-r["gd"], -r["gf"], -r["agf"], -r["w"], r["team"]))
        out = final
    for i, r in enumerate(out, 1):
        r["pos"] = i
        del r["agf"], r["aw"]
    return out


def ties(matches: list, rnd: str) -> list:
    games = [m for m in matches if m.get("round") == rnd]
    pairs: dict[frozenset, list] = {}
    for m in games:
        pairs.setdefault(frozenset((m["home"], m["away"])), []).append(m)
    out = []
    for legs in pairs.values():
        legs.sort(key=lambda m: m["date"])
        a, b = legs[0]["home"], legs[0]["away"]  # a hosts the first leg
        played = [m for m in legs if "hg" in m]
        ga = sum(m["hg"] if m["home"] == a else m["ag"] for m in played)
        gb = sum(m["hg"] if m["home"] == b else m["ag"] for m in played)
        last = legs[-1]
        winner = None
        if len(played) == len(legs) and played:
            if ga != gb:
                winner = a if ga > gb else b
            elif last.get("pens"):
                ph, pa = last["pens"]
                winner = last["home"] if ph > pa else last["away"]
        tie = {"a": a, "b": b, "agg": [ga, gb], "winner": winner,
               "legs": [{k: m.get(k) for k in ("date", "home", "away", "hg", "ag", "et", "pens")} for m in legs]}
        if any(m.get("et") for m in played):
            tie["et"] = True
        if last.get("pens"):
            tie["pens"] = last["pens"] if last["home"] == a else last["pens"][::-1]
        out.append(tie)
    return out


STAGE_RANK = {"first": 0, "PO": 1, "R16": 2, "QF": 3, "SF": 4, "F": 5, "W": 6}


def season_block(season: str, matches: list, countries: dict) -> dict:
    fmt = FORMAT[season]
    if fmt == "groups":
        assign_groups(matches, GROUP_SEEDS.get(season, {}))
    first = [m for m in matches if m["phase"] == "first"]
    teams = sorted({t for m in first for t in (m["home"], m["away"])})
    blk = {"season": season, "format": fmt, "teams": len(teams)}
    if fmt == "groups":
        groups = {}
        for g in "ABCDEFGH":
            gm = [m for m in first if m["group"] == g]
            gt = sorted({t for m in gm for t in (m["home"], m["away"])})
            groups[g] = table(gm, gt, True)
        blk["groups"] = groups
    else:
        blk["league"] = table(first, teams, False)
    rounds = {}
    for rnd in ("PO", "R16", "QF", "SF", "F"):
        tt = ties(matches, rnd)
        if tt:
            rounds[rnd] = tt
    blk["rounds"] = rounds
    # how far each club went
    reach = {t: "first" for t in teams}
    for rnd in ("PO", "R16", "QF", "SF", "F"):
        for tie in rounds.get(rnd, []):
            for t in (tie["a"], tie["b"]):
                reach[t] = rnd
    if rounds.get("F") and rounds["F"][0]["winner"]:
        reach[rounds["F"][0]["winner"]] = "W"
        blk["champion"] = rounds["F"][0]["winner"]
        blk["runner_up"] = next(t for t in (rounds["F"][0]["a"], rounds["F"][0]["b"]) if t != blk["champion"])
    blk["reach"] = reach
    played = [m for m in matches if "hg" in m]
    blk["played"] = len(played)
    blk["scheduled"] = len(matches)
    blk["complete"] = "champion" in blk
    blk["last_date"] = max((m["date"] for m in played), default=None)
    blk["matches"] = matches
    blk["countries"] = {t: countries[t] for t in teams}
    return blk


def main() -> int:
    seasons = []
    for s in SEASONS:
        txt, csvp = RAW / f"cl_{s}.txt", RAW / f"cl_{s}.csv"
        if txt.exists():
            m, c = parse_txt(txt, s)
            src = "openfootball"
        elif csvp.exists():
            m, c = parse_csv(csvp)
            src = "manual"
        else:
            print(f"no data for {s}", file=sys.stderr)
            continue
        blk = season_block(s, m, c)
        blk["source"] = src
        seasons.append(blk)
        print(f"{s}: {blk['format']:6} {blk['teams']} teams, {blk['played']}/{blk['scheduled']} played, "
              f"champion={blk.get('champion', '-')} ({src})")
    OUT.write_text(json.dumps({"built": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "seasons": seasons},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT.parent)} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
