"""How strong is each league, so a 0.5 xG/90 in Israel is not read as a 0.5 in England.

League strength = mean ClubElo rating of the league's clubs on a given date
(api.clubelo.com/<YYYY-MM-DD> is a free CSV of every European club). ClubElo
does not rate South American clubs, so Brazil and Argentina use fixed
estimates, marked as such in the output.

The adjustment is a heuristic to calibrate later, not a fitted model:
attacking volume per 90 is scaled by exp(BETA * (league_elo - ref_elo) / 100),
about 6% per 100 Elo below the Premier League. Ratios (pass %, xG per shot)
and defensive counts are left alone; defensive counts depend more on how much a
team defends than on the league's level. The natural next step is to fit BETA
on players who moved between leagues and compare their per-90s before and after.
"""
from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path

from .leagues import LEAGUES

BETA = 0.06
REFERENCE = "ENG1"
ADJUSTED = {"goals", "assists", "xg", "npxg", "xa", "shots", "shots_on_target",
            "key_passes", "dribbles", "xg_chain"}

# ClubElo has no South American clubs. Rough placement between the
# Championship and the Eredivisie; replace with a fitted value when available.
ESTIMATES = {"BRA1": 1640, "ARG1": 1580}


def fetch_clubelo(date: str) -> list[dict]:
    import requests
    r = requests.get(f"http://api.clubelo.com/{date}", timeout=30)
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


def league_elos(date: str, cache_dir: Path) -> dict[str, dict]:
    cache = cache_dir / f"clubelo_{date}.json"
    if cache.exists():
        clubs = json.loads(cache.read_text(encoding="utf-8"))
    else:
        clubs = fetch_clubelo(date)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(clubs), encoding="utf-8")
    out = {}
    for code, lg in LEAGUES.items():
        if code in ESTIMATES:
            out[code] = {"elo": ESTIMATES[code], "estimated": True}
            continue
        elos = [float(c["Elo"]) for c in clubs
                if c["Country"] == lg["clubelo"] and str(c["Level"]) == str(lg["level"])]
        if elos:
            out[code] = {"elo": round(sum(elos) / len(elos)), "estimated": False}
    return out


def factors(elos: dict[str, dict]) -> dict[str, float]:
    ref = elos[REFERENCE]["elo"]
    return {code: round(math.exp(BETA * (e["elo"] - ref) / 100), 3) for code, e in elos.items()}
