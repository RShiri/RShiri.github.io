"""Fetch real F1 season data for the dashboard.

Data sources — both reachable without the blocked live-timing / Ergast APIs:

* **Calendar** — ``fastf1.get_event_schedule`` (real rounds, names, dates, venues).
* **Results & standings** — the open-source **f1db** dataset, read straight from
  its committed source YAML on ``raw.githubusercontent.com`` (authoritative and
  updated through the current season, 2025 *and* 2026).

Writes ``web/data/<year>.json`` in the schema the ``web/`` dashboard consumes.
The pure ``assemble_season`` builder is decoupled from the network for testing.

    python fetch_season.py --year 2025
    python fetch_season.py                 # both 2025 and 2026
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("fetch_season")

F1DB = "https://raw.githubusercontent.com/f1db/f1db/main/src/data"

# f1db records only full pit-LANE time (drive-through + stationary), which is
# dominated by each circuit's lane length. We estimate the stationary
# tyre-change time by subtracting the race's fastest stop (≈ the shared
# drive-through), flooring the quickest stop at this nominal best.
PIT_STATIONARY_BASE = 2.0

# f1db constructorId -> display name (aligned with the front-end colour map).
# Era-correct display names (f1db uses distinct constructorIds across eras).
TEAM_NAMES = {
    "mclaren": "McLaren", "ferrari": "Ferrari", "mercedes": "Mercedes",
    "red-bull": "Red Bull Racing", "aston-martin": "Aston Martin", "alpine": "Alpine",
    "williams": "Williams", "haas": "Haas", "audi": "Audi", "cadillac": "Cadillac",
    "alphatauri": "AlphaTauri", "rb": "RB", "racing-bulls": "Racing Bulls",
    "alfa-romeo": "Alfa Romeo", "sauber": "Sauber", "kick-sauber": "Kick Sauber",
}

# fastf1 event name (lowercased, minus "grand prix") -> f1db grand-prix slug.
# Country/locality are tried as extra candidates, so this only needs oddities.
GP_SLUGS = {
    "australian": "australia", "chinese": "china", "japanese": "japan",
    "bahrain": "bahrain", "saudi arabian": "saudi-arabia", "miami": "miami",
    "emilia romagna": "emilia-romagna", "monaco": "monaco", "spanish": "spain",
    "canadian": "canada", "austrian": "austria", "british": "great-britain",
    "belgian": "belgium", "hungarian": "hungary", "dutch": "netherlands",
    "italian": "italy", "azerbaijan": "azerbaijan", "singapore": "singapore",
    "united states": "united-states", "mexico city": "mexico", "mexican": "mexico",
    "são paulo": "sao-paulo", "sao paulo": "sao-paulo", "brazilian": "sao-paulo",
    "las vegas": "las-vegas", "qatar": "qatar", "abu dhabi": "abu-dhabi",
    "portuguese": "portugal", "french": "france",
}


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def _parse_seconds(t) -> Optional[float]:
    """f1db time string -> float seconds. ``'13.341'`` or ``'1:02.5'``; None if bad."""
    if t is None:
        return None
    s = str(t).strip()
    if not s:
        return None
    try:
        if ":" in s:
            mins, secs = s.split(":", 1)
            return int(mins) * 60 + float(secs)
        return float(s)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Network layer (only touches raw.githubusercontent.com)
# --------------------------------------------------------------------------- #
_session = None
_yaml_cache: dict[str, object] = {}


def _get_yaml(path: str, retries: int = 3):
    """GET + parse an f1db YAML file. Returns parsed data, or None on 404/failure."""
    if path in _yaml_cache:
        return _yaml_cache[path]
    global _session
    import requests
    import yaml

    if _session is None:
        _session = requests.Session()
    url = f"{F1DB}/{path}"
    for attempt in range(retries):
        try:
            resp = _session.get(url, timeout=25)
            if resp.status_code == 404:
                _yaml_cache[path] = None
                return None
            resp.raise_for_status()
            data = yaml.safe_load(resp.text)
            _yaml_cache[path] = data
            return data
        except requests.RequestException as exc:
            if attempt == retries - 1:
                log.warning("Failed to fetch %s: %s", path, exc)
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


# --------------------------------------------------------------------------- #
# Resolvers (cached)
# --------------------------------------------------------------------------- #
_driver_cache: dict[str, dict] = {}
_country_cache: dict[str, str] = {}


def country_alpha2(country_id) -> str:
    """f1db ``countryId`` -> ISO alpha-2 code (drives flag emoji). '' if unknown."""
    if not country_id:
        return ""
    if country_id in _country_cache:
        return _country_cache[country_id]
    info = _get_yaml(f"countries/{country_id}.yml") or {}
    code = str(info.get("alpha2Code") or "").upper()
    _country_cache[country_id] = code
    return code


def resolve_driver(driver_id: str) -> dict:
    """``driverId`` -> ``{code, name, nat}`` (from the f1db driver file)."""
    if driver_id in _driver_cache:
        return _driver_cache[driver_id]
    info = _get_yaml(f"drivers/{driver_id}.yml") or {}
    name = info.get("name") or driver_id.replace("-", " ").title()
    last = str(info.get("lastName") or driver_id.split("-")[-1])
    code = info.get("abbreviation") or last[:3].upper()
    nat = country_alpha2(info.get("nationalityCountryId"))
    out = {"code": code, "name": name, "nat": nat}
    _driver_cache[driver_id] = out
    return out


def team_name(constructor_id: Optional[str]) -> str:
    if not constructor_id:
        return ""
    return TEAM_NAMES.get(constructor_id, constructor_id.replace("-", " ").title())


# --------------------------------------------------------------------------- #
# Per-race fetch
# --------------------------------------------------------------------------- #
def _slug_candidates(event_name: str, country: str, locality: str) -> list[str]:
    name = (event_name or "").lower().replace(" grand prix", "").strip()
    cands = []
    if name in GP_SLUGS:
        cands.append(GP_SLUGS[name])
    for token in (name, locality, country):
        s = _slugify(token)
        if s and s not in cands:
            cands.append(s)
    return cands


def _fetch_race_results(year: int, rnd: int, candidates: list[str]):
    """Return ``(results_list, slug)`` for a completed race, or ``(None, None)``."""
    for slug in candidates:
        data = _get_yaml(f"seasons/{year}/races/{rnd:02d}-{slug}/race-results.yml")
        if data:
            return data, slug
    return None, None


def _race_stat_maps(year: int, rnd: int, slug: str):
    """Pull the extra per-race f1db files that feed season statistics.

    Returns ``(pit_stops, pit_est, qpos, dotd_code)`` keyed by driver code:
    stop counts, per-stop *estimated stationary* times (s), qualifying
    position, and the Driver-of-the-Day winner. Any missing file degrades to
    empty/None.
    """
    base = f"seasons/{year}/races/{rnd:02d}-{slug}"

    pit_stops: dict[str, int] = {}
    raw_times: dict[str, list[float]] = {}
    pit = _get_yaml(f"{base}/pit-stops.yml")
    has_pit = isinstance(pit, list)
    if has_pit:
        for p in pit:
            code = resolve_driver(p.get("driverId", ""))["code"]
            pit_stops[code] = pit_stops.get(code, 0) + 1
            sec = _parse_seconds(p.get("time"))
            if sec is not None:
                raw_times.setdefault(code, []).append(sec)
    # Strip the circuit's drive-through so what remains ≈ the stationary time.
    pit_est: dict[str, list[float]] = {}
    all_times = [t for ts in raw_times.values() for t in ts]
    if all_times:
        lane = min(all_times) - PIT_STATIONARY_BASE
        pit_est = {code: [round(t - lane, 3) for t in ts] for code, ts in raw_times.items()}

    qpos: dict[str, int] = {}
    qual = _get_yaml(f"{base}/qualifying-results.yml")
    if isinstance(qual, list):
        for q in qual:
            code = resolve_driver(q.get("driverId", ""))["code"]
            qp = q.get("position")
            if isinstance(qp, int) and code not in qpos:
                qpos[code] = qp

    dotd = None
    dotd_rows = _get_yaml(f"{base}/driver-of-the-day-results.yml")
    if isinstance(dotd_rows, list):
        for row in dotd_rows:
            if row.get("position") == 1:
                dotd = resolve_driver(row.get("driverId", ""))["code"]
                break

    return pit_stops if has_pit else None, pit_est, qpos, dotd


def build_race(year: int, ev: dict, now: datetime, wins: dict) -> dict:
    """Assemble one race dict; fetches f1db results if the race is in the past."""
    race = {
        "round": ev["round"], "name": ev["name"], "country": ev["country"],
        "locality": ev["locality"], "circuit": ev["circuit"], "date": ev["date"],
        "status": "upcoming", "winner": None, "podium": [], "fastest_lap": None, "results": [],
    }
    if not (ev["date"] and ev["date"] <= now.strftime("%Y-%m-%d")):
        return race  # future race — don't probe

    candidates = _slug_candidates(ev["name"], ev["country"], ev["locality"])
    results, slug = _fetch_race_results(year, ev["round"], candidates)
    if not results:
        return race  # completed but not yet in f1db

    pit_stops, pit_est, qpos, dotd = _race_stat_maps(year, ev["round"], slug)

    rows = []
    for r in results:
        drv = resolve_driver(r.get("driverId", ""))
        pos = r.get("position")
        code = drv["code"]
        rows.append({
            "pos": int(pos) if isinstance(pos, int) else None,
            "code": code, "name": drv["name"], "nat": drv["nat"],
            "team": team_name(r.get("constructorId")),
            "grid": r.get("gridPosition") if isinstance(r.get("gridPosition"), int) else None,
            "points": r.get("points") or 0,
            "laps": r.get("laps") if isinstance(r.get("laps"), int) else None,
            "status": "Finished" if not r.get("reasonRetired") else str(r.get("reasonRetired")),
            "qpos": qpos.get(code),
            "stops": (pit_stops.get(code, 0) if pit_stops is not None else None),
            "pit_est": pit_est.get(code) or None,
        })
    rows.sort(key=lambda e: (e["pos"] is None, e["pos"] or 0))

    race["status"] = "completed"
    race["results"] = rows
    race["dotd"] = dotd
    race["podium"] = [{"pos": r["pos"], "code": r["code"], "name": r["name"],
                       "nat": r["nat"], "team": r["team"]}
                      for r in rows if r["pos"] in (1, 2, 3)]
    if race["podium"]:
        w = race["podium"][0]
        race["winner"] = {"code": w["code"], "name": w["name"], "nat": w["nat"], "team": w["team"]}
        wins["drivers"][w["code"]] = wins["drivers"].get(w["code"], 0) + 1
        wins["teams"][w["team"]] = wins["teams"].get(w["team"], 0) + 1

    fl = _get_yaml(f"seasons/{year}/races/{ev['round']:02d}-{slug}/fast-laps.yml")
    if isinstance(fl, list) and fl:
        d = resolve_driver(fl[0].get("driverId", ""))
        race["fastest_lap"] = {"code": d["code"], "name": d["name"], "time": str(fl[0].get("time") or "")}
    return race


# --------------------------------------------------------------------------- #
# Season statistics (pure aggregation over completed-race results)
# --------------------------------------------------------------------------- #
def build_driver_stats(races: list, team_by_code: dict,
                       points_by_code: Optional[dict] = None) -> list:
    """Aggregate per-driver season stats from completed races.

    Pure function of the race dicts (result rows + ``race['dotd']``), so it is
    unit-testable without the network. Emits one row per driver who started at
    least one race, sorted by championship points.

    Wins / podiums / poles are Grand-Prix figures (the conventional meaning).
    ``points`` uses the official ``points_by_code`` championship total when
    given — that includes sprint points, which the per-GP results omit — and
    otherwise falls back to the summed race points.
    """
    points_by_code = points_by_code or {}
    acc: dict[str, dict] = {}

    def slot(row) -> dict:
        code = row["code"]
        if code not in acc:
            acc[code] = {
                "code": code, "name": row["name"], "nat": row.get("nat", ""),
                "starts": 0, "wins": 0, "podiums": 0, "poles": 0, "points": 0.0,
                "pts_fin": 0, "dnf": 0, "laps": 0, "dotd": 0,
                "grid": [], "fin": [], "gain": 0,
                "stops": [], "pit_est": [],
                "led": 0, "led_any": False,
            }
        return acc[code]

    for race in races:
        if race.get("status") != "completed":
            continue
        for row in race.get("results", []):
            a = slot(row)
            pos, grid = row.get("pos"), row.get("grid")
            a["starts"] += 1
            a["points"] += row.get("points") or 0
            a["laps"] += row.get("laps") or 0
            if pos == 1:
                a["wins"] += 1
            if isinstance(pos, int) and pos <= 3:
                a["podiums"] += 1
            if isinstance(pos, int) and pos <= 10:
                a["pts_fin"] += 1
            if row.get("qpos") == 1:
                a["poles"] += 1
            if row.get("status") and row["status"] != "Finished":
                a["dnf"] += 1
            if isinstance(grid, int) and grid > 0:
                a["grid"].append(grid)
            if isinstance(pos, int):
                a["fin"].append(pos)
            if isinstance(grid, int) and grid > 0 and isinstance(pos, int):
                a["gain"] += grid - pos
            stops = row.get("stops")
            if isinstance(stops, int):
                a["stops"].append(stops)
            est = row.get("pit_est")
            if est:
                a["pit_est"].extend(est)
            led = row.get("led")
            if led is not None:
                a["led"] += led
                a["led_any"] = True
        winner = race.get("dotd")
        if winner in acc:
            acc[winner]["dotd"] += 1

    def mean(xs, nd=1):
        return round(sum(xs) / len(xs), nd) if xs else None

    out = []
    for a in acc.values():
        pts = points_by_code.get(a["code"], a["points"])
        out.append({
            "code": a["code"], "name": a["name"], "nat": a["nat"],
            "team": team_by_code.get(a["code"], ""),
            "starts": a["starts"], "wins": a["wins"], "podiums": a["podiums"],
            "poles": a["poles"], "pts_fin": a["pts_fin"], "dnf": a["dnf"],
            "points": int(pts) if float(pts).is_integer() else round(pts, 1),
            "avg_grid": mean(a["grid"]), "avg_finish": mean(a["fin"]),
            "gained": a["gain"],
            "avg_stops": mean(a["stops"]),
            "stop_s": round(statistics.median(a["pit_est"]), 2) if a["pit_est"] else None,
            "dotd": a["dotd"], "laps": a["laps"],
            "laps_led": a["led"] if a["led_any"] else None,
        })
    out.sort(key=lambda s: (-float(s["points"]),
                            s["avg_finish"] if s["avg_finish"] is not None else 99))
    return out


def enrich_laps_led(year: int, races: list) -> None:
    """Optional: fill each result row's ``led`` (laps led) via fastf1 lap timing.

    Laps-led is the one requested stat the public f1db dataset does not carry, so
    it must come from lap-by-lap timing. That needs live-timing network access,
    which is unavailable in many environments — this degrades to a no-op per race
    wherever the session cannot load, leaving ``led`` absent (the UI hides the
    column). Off by default; opt in with ``--laps-led`` / ``F1_LAPS_LED=1``.
    """
    import fastf1

    for race in races:
        if race.get("status") != "completed":
            continue
        try:
            ses = fastf1.get_session(year, race["round"], "R")
            ses.load(laps=True, telemetry=False, weather=False, messages=False)
            laps = ses.laps
            leaders = laps.loc[laps["Position"] == 1]
            led = leaders.groupby("Driver")["LapNumber"].nunique().to_dict()
            for row in race.get("results", []):
                if row["code"] in led:
                    row["led"] = int(led[row["code"]])
        except Exception as exc:  # noqa: BLE001 — timing simply unavailable here
            log.warning("laps-led unavailable for %s R%s: %s", year, race["round"], exc)


# --------------------------------------------------------------------------- #
# Season assembly
# --------------------------------------------------------------------------- #
def assemble_season(year, races, driver_standings, constructor_standings,
                    team_by_code, wins, now) -> dict:
    """Pure assembler: combine fetched pieces into the dashboard schema."""
    drivers = []
    for s in driver_standings or []:
        drv = resolve_driver(s.get("driverId", ""))
        drivers.append({
            "pos": s.get("position"), "code": drv["code"], "name": drv["name"],
            "nat": drv["nat"], "team": team_by_code.get(drv["code"], ""),
            "points": s.get("points") or 0, "wins": wins["drivers"].get(drv["code"], 0),
        })
    constructors = []
    for s in constructor_standings or []:
        tm = team_name(s.get("constructorId"))
        constructors.append({
            "pos": s.get("position"), "team": tm,
            "points": s.get("points") or 0, "wins": wins["teams"].get(tm, 0),
        })
    points_by_code = {d["code"]: d["points"] for d in drivers}
    return {
        "season": int(year), "updated": now.isoformat(), "source": "f1db + fastf1",
        "races": races, "drivers": drivers, "constructors": constructors,
        "stats": build_driver_stats(races, team_by_code, points_by_code),
    }


def _team_by_code(year: int, races: list) -> dict:
    """driver code -> current team: season entrants, overridden by latest race."""
    out: dict[str, str] = {}
    for ent in _get_yaml(f"seasons/{year}/entrants.yml") or []:
        tm = team_name(ent.get("constructorId"))
        for d in ent.get("drivers", []) or []:
            if d.get("rounds") and not d.get("testDriver"):
                out[resolve_driver(d["driverId"])["code"]] = tm
    for race in races:  # earliest -> latest, so the most recent team wins
        for r in race.get("results", []):
            if r["team"]:
                out[r["code"]] = r["team"]
    return out


def reconcile_postponed(races: list) -> None:
    """Flag a past, result-less race as ``postponed`` when a later round is done.

    The calendar comes from fastf1, but results come from f1db. When a scheduled
    race never takes place (postponed or cancelled), f1db simply omits that round
    — yet fastf1 may keep listing it with its original date. Such a race would
    otherwise sit forever as ``upcoming`` with a past date, indistinguishable from
    one whose results merely haven't been published yet.

    The unambiguous signal that a round was *skipped* is that a higher-numbered
    round has already been completed: races run in round order, so a later result
    can never precede an earlier one. (A race that has only just happened has no
    later round completed, so it correctly stays ``upcoming`` until f1db catches
    up.) Mutates ``races`` in place.
    """
    latest_done = max((r["round"] for r in races
                       if r.get("status") == "completed"), default=0)
    for r in races:
        if r.get("status") == "upcoming" and r.get("round", 0) < latest_done:
            r["status"] = "postponed"


# --------------------------------------------------------------------------- #
# Manual race backfill — a stopgap for rounds f1db has not ingested yet.
# --------------------------------------------------------------------------- #
def load_manual_races() -> dict:
    """Load committed manual race results, keyed by ``(year, round)``.

    Each ``data/manual_races/*.json`` holds one race in the dashboard schema,
    tagged with its ``year`` and ``round`` and a ``source``. They cover races
    the public f1db dataset has not published yet; each is applied only while
    f1db lacks that round (see ``apply_manual_races``).
    """
    out: dict = {}
    manual_dir = config.DATA_DIR / "manual_races"
    if not manual_dir.is_dir():
        return out
    for path in sorted(manual_dir.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            out[(int(doc["year"]), int(doc["round"]))] = doc["race"]
        except (ValueError, KeyError) as exc:  # noqa: PERF203 — tiny, tolerant loop
            log.warning("Skipping bad manual race %s: %s", path, exc)
    return out


def apply_manual_races(year: int, races: list, wins: dict) -> list:
    """Fill rounds f1db is still missing from committed manual results.

    Replaces a not-yet-completed race with its manual result (when one exists)
    and registers the win. Returns the manual races actually applied so the
    standings can be topped up with their points. A round f1db already has is
    left untouched, so f1db silently supersedes the stopgap once it catches up.
    Mutates the matching race dicts in ``races`` in place.
    """
    manual = load_manual_races()
    applied = []
    for r in races:
        m = manual.get((year, r.get("round")))
        if m and r.get("status") != "completed":
            r.clear()
            r.update(m)
            w = r.get("winner")
            if w:
                wins["drivers"][w["code"]] = wins["drivers"].get(w["code"], 0) + 1
                wins["teams"][w["team"]] = wins["teams"].get(w["team"], 0) + 1
            applied.append(r)
    return applied


def topup_standings(driver_standings: list, constructor_standings: list,
                    applied_races: list) -> tuple:
    """Fold manually-applied race points into the f1db standings and re-rank.

    f1db's standings omit any round it has not ingested, so when a manual race
    fills that gap its points must be added or the championship would trail the
    results shown by a round. Points are matched by driver code / team name; the
    re-sort is stable, preserving f1db's countback order on ties.
    """
    dpts: dict = {}
    cpts: dict = {}
    for race in applied_races:
        for row in race.get("results", []):
            pts = row.get("points") or 0
            if not pts:
                continue
            dpts[row["code"]] = dpts.get(row["code"], 0) + pts
            if row.get("team"):
                cpts[row["team"]] = cpts.get(row["team"], 0) + pts
    if not dpts and not cpts:
        return driver_standings, constructor_standings

    for s in driver_standings:
        code = resolve_driver(s.get("driverId", ""))["code"]
        s["points"] = (s.get("points") or 0) + dpts.get(code, 0)
    driver_standings = sorted(driver_standings, key=lambda s: -(s.get("points") or 0))
    for i, s in enumerate(driver_standings, 1):
        s["position"] = i

    for s in constructor_standings:
        tm = team_name(s.get("constructorId"))
        s["points"] = (s.get("points") or 0) + cpts.get(tm, 0)
    constructor_standings = sorted(constructor_standings, key=lambda s: -(s.get("points") or 0))
    for i, s in enumerate(constructor_standings, 1):
        s["position"] = i
    return driver_standings, constructor_standings


def fetch_season(year: int, now: Optional[datetime] = None, laps_led: bool = False) -> dict:
    """Fetch one season from fastf1 (calendar) + f1db (results/standings)."""
    import fastf1
    import pandas as pd

    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(config.CACHE_DIR))
    now = now or datetime.now(timezone.utc)

    schedule_df = fastf1.get_event_schedule(year, include_testing=False)
    events = []
    for _, ev in schedule_df.iterrows():
        rnd = int(ev["RoundNumber"])
        if rnd < 1:
            continue
        d = pd.to_datetime(ev.get("Session5DateUtc") or ev.get("EventDate"))
        events.append({
            "round": rnd, "name": str(ev["EventName"]), "country": str(ev.get("Country", "")),
            "locality": str(ev.get("Location", "")), "circuit": str(ev.get("Location", "")),
            "date": d.strftime("%Y-%m-%d") if pd.notna(d) else "",
        })

    wins = {"drivers": {}, "teams": {}}
    races = [build_race(year, ev, now, wins) for ev in events]
    applied_manual = apply_manual_races(year, races, wins)
    reconcile_postponed(races)
    if laps_led:
        enrich_laps_led(year, races)

    driver_standings = _get_yaml(f"seasons/{year}/driver-standings.yml") or []
    constructor_standings = _get_yaml(f"seasons/{year}/constructor-standings.yml") or []
    driver_standings, constructor_standings = topup_standings(
        driver_standings, constructor_standings, applied_manual)
    team_by_code = _team_by_code(year, races)

    season = assemble_season(year, races, driver_standings, constructor_standings,
                             team_by_code, wins, now)
    done = sum(1 for r in races if r["status"] == "completed")
    log.info("%s: %d races (%d completed), %d drivers, %d constructors.",
             year, len(races), done, len(season["drivers"]), len(season["constructors"]))
    return season


def write_season_json(season: dict, year: int, out_dir: Optional[Path] = None) -> Path:
    out_dir = out_dir or (config.ROOT_DIR / "web" / "data")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{year}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(season, fh, ensure_ascii=False, indent=1, default=str)
    log.info("Wrote %s", path)
    return path


def main(argv=None):
    import os

    p = argparse.ArgumentParser(description="Fetch real F1 season data for the dashboard.")
    p.add_argument("--year", type=int, action="append", help="Season(s); repeatable.")
    p.add_argument("--laps-led", action="store_true",
                   help="Also compute laps-led via fastf1 lap timing (needs live-timing access).")
    args = p.parse_args(argv)
    laps_led = args.laps_led or os.environ.get("F1_LAPS_LED") == "1"
    for y in (args.year or [2025, 2026]):
        try:
            write_season_json(fetch_season(y, laps_led=laps_led), y)
        except Exception as exc:
            log.warning("Could not fetch %s: %s", y, exc)


if __name__ == "__main__":
    main()
