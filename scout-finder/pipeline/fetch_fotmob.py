"""Pull every player's per-match stats for a league-season from FotMob.

  python -m pipeline.fetch_fotmob --check                    # verify league ids
  python -m pipeline.fetch_fotmob --league ENG1 --season 2025-26
  python -m pipeline.fetch_fotmob --all --season 2025-26     # the whole universe

One matchDetails request per finished match. Every response is cached under
data/raw/fotmob/<match_id>.json, so a run that dies (rate limit, laptop sleeps)
resumes where it stopped and a rebuild never re-fetches. Output is one CSV per
league-season, one row per player per match, in the same columns XEPL writes,
so sources/fotmob.py reads both.

FotMob serves /api/data/* to clients with a browser TLS fingerprint, so this
uses curl_cffi (pip install curl_cffi), the same trick XEPL's scraper uses.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
from pathlib import Path

from .leagues import CALENDAR_YEAR, LEAGUES

BASE = "https://www.fotmob.com/api/data"
DATA = Path(__file__).resolve().parent.parent / "data"
RAW = DATA / "raw" / "fotmob"
PAUSE = (1.5, 3.0)  # seconds between uncached requests; be a polite client

_session = None


def _get(path: str) -> dict:
    global _session
    if _session is None:
        from curl_cffi import requests as cr
        _session = cr.Session(impersonate="chrome")
    for attempt in range(4):
        r = _session.get(f"{BASE}{path}", timeout=30,
                         headers={"Referer": "https://www.fotmob.com/"})
        if r.status_code == 200:
            return r.json()
        if r.status_code in (403, 429, 503):
            time.sleep(20 * (attempt + 1))
            continue
        r.raise_for_status()
    raise RuntimeError(f"FotMob kept refusing {path} (last HTTP {r.status_code})")


def fotmob_season(code: str, season: str) -> str:
    """'2025-26' -> '2025/2026' (FotMob's label); calendar-year leagues use '2026'."""
    if code in CALENDAR_YEAR:
        # The calendar year that starts inside the European season, e.g. 2025-26 -> 2025.
        return season[:4]
    start = int(season[:4])
    return f"{start}/{start + 1}"


def league_matches(code: str, season: str) -> list[dict]:
    """Finished matches of a league-season: id, date, home, away."""
    lg = LEAGUES[code]
    data = _get(f"/leagues?id={lg['fotmob']}&season={fotmob_season(code, season)}")
    out = []
    for m in data.get("fixtures", {}).get("allMatches", []):
        st = m.get("status", {})
        if st.get("finished") and not st.get("cancelled"):
            out.append({"id": int(m["id"]), "date": st.get("utcTime", "")[:10],
                        "home": m["home"]["name"], "away": m["away"]["name"]})
    return out


def match_details(match_id: int) -> dict:
    cache = RAW / f"{match_id}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    time.sleep(random.uniform(*PAUSE))
    data = _get(f"/matchDetails?matchId={match_id}")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data


# FotMob stat key -> XEPL column, checked against live matchDetails (Oct 2026).
# Fraction stats come as {"value": made, "total": attempted}; older or XEPL-cached
# responses may carry "34/40 (85%)" strings instead, so _value accepts both.
# Leagues without Opta xG (e.g. Israel) simply omit expected_goals/expected_assists.
STAT_KEYS = {
    "minutes_played": "minutes",
    "goals": "goals",
    "assists": "assists",
    "expected_goals": "xg",
    "expected_goals_non_penalty": "npxg",
    "expected_goals_on_target_variant": "xgot",
    "expected_assists": "xa",
    "total_shots": "shots",
    "ShotsOnTarget": "sot",
    "big_chance_missed_title": "bigChancesMissed",
    "chances_created": "keyPasses",
    "big_chance_created_team_title": "bigChancesCreated",
    "accurate_passes": ("passAcc", "passes"),
    "passes_into_final_third": "finalThirdPasses",
    "accurate_crosses": ("crossesAcc", "crosses"),
    "long_balls_accurate": ("longBallsAcc", "longBalls"),
    "touches": "touches",
    "touches_opp_box": "boxTouches",
    "dribbles_succeeded": ("dribbles", "dribblesAtt"),
    "dispossessed": "dispossessed",
    "was_fouled": "wasFouled",
    "matchstats.headers.tackles": "tackles",
    "interceptions": "interceptions",
    "recoveries": "recoveries",
    "clearances": "clearances",
    "shot_blocks": "blocks",
    "dribbled_past": "dribbledPast",
    "ground_duels_won": ("groundDuelsWon", "groundDuels"),
    "aerials_won": ("aerials", "aerialsAtt"),
    "fouls": "fouls",
    # Keepers
    "saves": "saves",
    "saves_inside_box": "savesInsideBox",
    "goals_conceded": "goalsConceded",
    "expected_goals_on_target_faced": "xgotFaced",
    "goals_prevented": "goalsPrevented",
    "keeper_sweeper": "sweeperActions",
    "keeper_high_claim": "highClaims",
    "rating_title": "rating",
}
# Line-breaking passes and the physical metrics (distance, sprints) exist only
# for the Premier League, so they are left out: a metric must cover the universe.
COUNT_COLS = {c for v in STAT_KEYS.values() for c in (v if isinstance(v, tuple) else (v,))
              } - {"rating", "minutes"}
_FRACTION = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")


def _value(stat: dict):
    """A FotMob stat cell -> number, or (made, attempted) for fraction stats."""
    s = stat.get("stat", stat)
    v, total = s.get("value"), s.get("total")
    if total is not None and v is not None:
        return float(v), float(total)
    if isinstance(v, str):
        m = _FRACTION.match(v)
        if m:
            return float(m.group(1)), float(m.group(2))
        try:
            return float(v)
        except ValueError:
            return None
    return float(v) if isinstance(v, (int, float)) else None


def _lineup_info(details: dict) -> dict[int, dict]:
    """player id -> age, market value (EUR) and nationality, as the lineup lists them."""
    info = {}
    lineup = details.get("content", {}).get("lineup", {}) or {}
    for side in ("homeTeam", "awayTeam"):
        team = lineup.get(side) or {}
        for p in (team.get("starters") or []) + (team.get("subs") or []):
            info[int(p["id"])] = {"age": p.get("age"), "valueEur": p.get("marketValue"),
                                  "country": p.get("countryName")}
    return info


def _possession(details: dict) -> dict:
    """team id -> that team's ball possession in the match (%), when FotMob gives it."""
    general = details.get("general", {})
    home, away = general.get("homeTeam", {}).get("id"), general.get("awayTeam", {}).get("id")
    periods = (details.get("content", {}).get("stats") or {}).get("Periods") or {}
    for section in (periods.get("All") or {}).get("stats") or []:
        for st in section.get("stats") or []:
            if st.get("key") == "BallPossesion" and all(isinstance(v, (int, float))
                                                         for v in st.get("stats", [])):
                h, a = st["stats"]
                return {home: h, away: a}
    return {}


def _positions(details: dict) -> dict[int, str]:
    """player id -> lineup position label.

    Starters get their slot. Subs have no positionId, only usualPlayingPositionId,
    so they get 'Sub:<coarse slot>': not counted as a start, but a fallback for
    players who never started (see sources/fotmob._main_group).
    """
    pos = {}
    lineup = details.get("content", {}).get("lineup", {}) or {}
    for side in ("homeTeam", "awayTeam"):
        team = lineup.get(side) or {}
        for p in team.get("starters", []) or []:
            pos[int(p["id"])] = slot_from_fotmob(p)
        for p in team.get("subs", []) or []:
            coarse = COARSE.get(p.get("usualPlayingPositionId"), "")
            pos[int(p["id"])] = f"Sub:{coarse}" if coarse else "Sub"
    return pos


# FotMob lineup positionId -> WhoScored-style slot (positions.py understands these).
# The id encodes the row (1x GK, 3x back line, 5x/6x wing-back & pivot, 7x midfield,
# 8x attacking midfield, 10x/115 forwards) and the column (low digit = right side).
# Checked against live lineups and their pitch coordinates: 83/87 are the wide
# men of a 4-2-3-1 (mostly forwards by trade), 84/86 the two 8s of a 4-1-4-1 or
# the two 10s of a 3-4-2-1, 62/68 the wing-backs of a 3-4-x.
# The 6x row is mapped to central midfield, not DM: 64/66 are the double pivot of
# a 4-2-3-1 / 3-4-2-1 (Pedri, Rice), 63/67 the side men of a 4-3-1-2, and 65 the
# lone pivot of a 4-1-4-1 or 3-1-4-2. FotMob draws a 4-3-3's anchor level with
# the 8s (75), so 65 alone left a DM group of 4 players (Rodri among them), too
# few to rank, and they fell out of the build. So the universe has no DM group.
# Unknown ids fall back to the coarse usualPlayingPositionId (0 GK, 1 DEF, 2 MID, 3 FWD).
POSITION_ID = {
    11: "GK",
    32: "DR", 33: "DC", 34: "DC", 35: "DC", 36: "DC", 37: "DC", 38: "DL",
    51: "DMR", 59: "DML", 62: "DMR", 68: "DML",
    63: "MC", 64: "MC", 65: "MC", 66: "MC", 67: "MC",
    71: "MR", 72: "MR", 73: "MC", 74: "MC", 75: "MC", 76: "MC", 77: "MC", 78: "ML", 79: "ML",
    82: "AMR", 83: "AMR", 84: "AMC", 85: "AMC", 86: "AMC", 87: "AML", 88: "AML",
    103: "FWR", 104: "FW", 105: "FW", 106: "FW", 107: "FWL", 115: "FW",
}
COARSE = {0: "GK", 1: "DC", 2: "MC", 3: "FW"}


def slot_from_fotmob(p: dict) -> str:
    pid = p.get("positionId")
    if pid in POSITION_ID:
        return POSITION_ID[pid]
    return COARSE.get(p.get("usualPlayingPositionId"), "")


def player_rows(match: dict, details: dict, league: str) -> list[dict]:
    general = details.get("general", {})
    teams = {general.get("homeTeam", {}).get("id"): general.get("homeTeam", {}).get("name"),
             general.get("awayTeam", {}).get("id"): general.get("awayTeam", {}).get("name")}
    positions = _positions(details)
    profile = _lineup_info(details)
    poss = _possession(details)
    rows = []
    for pid, p in (details.get("content", {}).get("playerStats") or {}).items():
        row = {"league": league, "match_id": match["id"], "date": match["date"],
               "player_id": int(pid), "player": p.get("name"), "teamId": p.get("teamId"),
               "team": teams.get(p.get("teamId")) or p.get("teamName"),
               "position": positions.get(int(pid), "")}
        row.update({k: v for k, v in profile.get(int(pid), {}).items() if v is not None})
        # Opponent's possession, for possession-adjusted defending (sources/fotmob.py).
        mine = poss.get(p.get("teamId"))
        if mine is not None:
            row["oppPossession"] = 100 - mine
        for section in p.get("stats", []):
            for stat in (section.get("stats") or {}).values():
                col = STAT_KEYS.get(stat.get("key"))
                if col is None:
                    continue
                v = _value(stat)
                if isinstance(col, tuple):
                    if isinstance(v, tuple):
                        row[col[0]], row[col[1]] = v
                elif isinstance(v, tuple):
                    row[col] = v[0]
                elif v is not None:
                    row[col] = v
        if row.get("minutes"):
            rows.append(row)
    # FotMob leaves a stat out when it is zero (no xG key for a player who never
    # shot, no dribbles key for one who never tried). So a stat that anyone in the
    # match has is 0 for the rest; a stat nobody has (no xG in this league) stays
    # missing. Rating is not a count: short cameos have none, and that is not 0.
    published = {k for r in rows for k in r if k in COUNT_COLS}
    for r in rows:
        for k in published:
            r.setdefault(k, 0.0)
    return rows


COLUMNS = ["league", "season", "match_id", "date", "team", "teamId", "player_id", "player",
           "position",
           "age", "valueEur", "country", "oppPossession", "minutes", "rating"] + sorted(
    COUNT_COLS)


def cached_matches(code: str, season: str) -> list[dict]:
    """The match list of an earlier run, from its CSV: re-parse without the network."""
    path = DATA / "fotmob" / f"{code}_{season}.csv"
    with path.open(encoding="utf-8") as fh:
        seen = {}
        for r in csv.DictReader(fh):
            seen.setdefault(r["match_id"], {"id": int(r["match_id"]), "date": r["date"],
                                            "home": "", "away": ""})
    return [m for m in seen.values() if (RAW / f"{m['id']}.json").exists()]


def fetch_league(code: str, season: str, offline: bool = False) -> Path:
    matches = cached_matches(code, season) if offline else league_matches(code, season)
    out = DATA / "fotmob" / f"{code}_{season}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open("w", newline="", encoding="utf-8") as fh:
        # Missing stats stay empty, never 0: a league without xG must not look like 0 xG.
        w = csv.DictWriter(fh, COLUMNS, extrasaction="ignore")
        w.writeheader()
        for i, m in enumerate(matches, 1):
            try:
                rows = player_rows(m, match_details(m["id"]), code)
                for r in rows:
                    r["season"] = season
            except Exception as exc:  # one bad match must not sink a 380-match run
                print(f"  ! {m['id']} {m['home']}-{m['away']}: {exc}")
                continue
            w.writerows(rows)
            n += len(rows)
            if i % 25 == 0:
                print(f"  {code}: {i}/{len(matches)} matches")
    print(f"{code} {season}: {len(matches)} matches, {n} player rows -> {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", action="append", default=[], choices=sorted(LEAGUES))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--season", default="2025-26")
    ap.add_argument("--check", action="store_true", help="print FotMob's name for each id")
    ap.add_argument("--offline", action="store_true",
                    help="re-parse the cached matches of an earlier run, no network")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # 'Série A' on a Windows console
    if a.check:
        for code, lg in LEAGUES.items():
            d = _get(f"/leagues?id={lg['fotmob']}")
            print(f"{code:5} {lg['fotmob']:>4}  expected {lg['name']!r:28} "
                  f"FotMob says {d.get('details', {}).get('name')!r}")
        return
    for code in (sorted(LEAGUES) if a.all else a.league):
        fetch_league(code, a.season, a.offline)


if __name__ == "__main__":
    main()
