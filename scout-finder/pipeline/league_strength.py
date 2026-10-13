"""How strong is each league, so a 0.5 xG/90 in Israel is not read as a 0.5 in England.

League strength = mean ClubElo rating of the league's clubs on a given date
(api.clubelo.com/<YYYY-MM-DD> is a free CSV of every club). When that API is
down (it returned 502 for every date in Oct 2026), the fallback reads the
per-country, per-level averages printed on the clubelo.com front page: those are
today's ratings and today's league membership, not the requested date's, and
the output says so. A league ClubElo does not rate falls back to a fixed estimate.

The adjustment is a heuristic to calibrate later, not a fitted model:
attacking volume per 90 is scaled by exp(BETA * (league_elo - ref_elo) / 100),
about 6% per 100 Elo below the Premier League. Ratios (pass %, xG per shot)
and defensive counts are left alone; defensive counts depend more on how much a
team defends than on the league's level. The natural next step is to fit BETA
on players who moved between leagues and compare their per-90s before and after.
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import math
import re
from pathlib import Path

from .leagues import LEAGUES

BETA = 0.06
REFERENCE = "ENG1"
ADJUSTED = {"goals", "assists", "xg", "npxg", "xa", "shots", "shots_on_target",
            "key_passes", "dribbles", "xg_chain"}

# Last resort when ClubElo has no rating for a league (it did not rate South
# American clubs until recently). Rough placement between the Championship and
# the Eredivisie.
ESTIMATES = {"BRA1": 1640, "ARG1": 1580}
SITE = "https://clubelo.com/"


def fetch_clubelo(date: str) -> list[dict]:
    import requests
    r = requests.get(f"http://api.clubelo.com/{date}", timeout=30)
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


_LEVEL = re.compile(r"Level (\d+) \((\d+) teams\)</i></td><td><i>⌀(\d+)")
_FLAG = re.compile(r'<img alt="([A-Z]{3})"')


def site_averages(html: str) -> dict[str, dict[int, int]]:
    """Front-page league averages: {country: {level: elo}}.

    Each 'Level N (k teams) ⌀elo' header row comes before its clubs, so its
    country is the flag on the first club row after it.
    """
    out: dict[str, dict[int, int]] = {}
    for m in _LEVEL.finditer(html):
        flag = _FLAG.search(html, m.end())
        if flag:
            out.setdefault(flag.group(1), {}).setdefault(int(m.group(1)), int(m.group(3)))
    return out


def league_elos(date: str, cache_dir: Path) -> dict[str, dict]:
    cache = cache_dir / f"clubelo_{date}.json"
    clubs = None
    if cache.exists():
        clubs = json.loads(cache.read_text(encoding="utf-8"))
    else:
        try:
            clubs = fetch_clubelo(date)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(clubs), encoding="utf-8")
        except Exception as exc:
            print(f"ClubElo API failed for {date} ({exc}); using today's clubelo.com averages")
    if clubs is None:
        return _site_league_elos(cache_dir)
    out = {}
    for code, lg in LEAGUES.items():
        elos = [float(c["Elo"]) for c in clubs
                if c["Country"] == lg["clubelo"] and str(c["Level"]) == str(lg["level"])]
        if elos:
            out[code] = {"elo": round(sum(elos) / len(elos)), "estimated": False,
                         "source": f"api.clubelo.com/{date}"}
        elif code in ESTIMATES:
            out[code] = {"elo": ESTIMATES[code], "estimated": True}
    return out


def _site_league_elos(cache_dir: Path) -> dict[str, dict]:
    import requests
    today = datetime.date.today().isoformat()
    cache = cache_dir / f"clubelo_site_{today}.html"
    if cache.exists():
        html = cache.read_text(encoding="utf-8")
    else:
        r = requests.get(SITE, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        html = r.text
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(html, encoding="utf-8")
    avg = site_averages(html)
    out = {}
    for code, lg in LEAGUES.items():
        elo = avg.get(lg["clubelo"] or "", {}).get(lg["level"])
        if elo:
            out[code] = {"elo": elo, "estimated": False, "source": f"clubelo.com {today}"}
        elif code in ESTIMATES:
            out[code] = {"elo": ESTIMATES[code], "estimated": True}
    return out


def factors(elos: dict[str, dict]) -> dict[str, float]:
    ref = elos[REFERENCE]["elo"]
    return {code: round(math.exp(BETA * (e["elo"] - ref) / 100), 3) for code, e in elos.items()}
