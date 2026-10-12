"""Understat: last season's xG, xA, npxG, xGChain and xGBuildup for the top-5 leagues.

One request per league-season returns every player's season totals, so this is
cheap. Understat keys a season by its START year (2025 = 2025-26).

Fetching, in order (Understat has changed this more than once, so each is tried):
  1. GET /getLeagueData/{league}/{year} with X-Requested-With + Referer headers,
     JSON with a "players" list.
  2. The league page's embedded `var playersData = JSON.parse('...')` blob.
  3. The same page loaded through a real browser (Selenium), because Understat
     bot-blocks plain HTTP at times (XEPL hit this; see epl/understat.py there).
Either way, a raw JSON dump is cached under data/raw/ so a rebuild never re-fetches.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from ..positions import group_from_understat

BASE = "https://understat.com"
LEAGUES = {"EPL": "EPL", "LaLiga": "La_liga", "SerieA": "Serie_A",
           "Bundesliga": "Bundesliga", "Ligue1": "Ligue_1"}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


def _decode_blob(raw: str):
    # Understat hex-escapes the JSON ("\x7B..."); undo that, then fix UTF-8 names.
    text = raw.encode("utf-8").decode("unicode_escape")
    try:
        text = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return json.loads(text)


def players_from_page(html: str) -> list[dict] | None:
    m = re.search(r"var\s+playersData\s*=\s*JSON\.parse\('(.+?)'\);", html, re.DOTALL)
    return _decode_blob(m.group(1)) if m else None


def fetch_players(league: str, start_year: int, use_browser: bool = False) -> list[dict]:
    slug = LEAGUES[league]
    page_url = f"{BASE}/league/{slug}/{start_year}"
    if not use_browser:
        import requests
        s = requests.Session()
        s.headers["User-Agent"] = UA
        r = s.get(f"{BASE}/getLeagueData/{slug}/{start_year}", timeout=30,
                  headers={"X-Requested-With": "XMLHttpRequest", "Referer": page_url})
        if r.ok and r.headers.get("content-type", "").startswith("application/json"):
            players = r.json().get("players")
            if players:
                return players
        r = s.get(page_url, timeout=30)
        players = players_from_page(r.text) if r.ok else None
        if players:
            return players
    # Last resort: a real browser.
    from selenium import webdriver
    opts = webdriver.ChromeOptions()
    opts.add_argument(f"user-agent={UA}")
    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(page_url)
        driver.implicitly_wait(5)
        players = players_from_page(driver.page_source)
    finally:
        driver.quit()
    if not players:
        raise RuntimeError(f"Understat returned no players for {league} {start_year}")
    return players


def to_rows(players: list[dict], league: str, season: str) -> pd.DataFrame:
    """Understat player records -> schema rows (season totals)."""
    f = lambda p, k: float(p.get(k) or 0)
    rows = []
    for p in players:
        rows.append({
            "source": "understat", "season": season, "league": league,
            "player_id": f"understat:{p['id']}",
            "name": p["player_name"],
            # A player who moved mid-season is listed as "Team A,Team B".
            "team": p["team_title"].split(",")[-1],
            "pos_group": group_from_understat(p.get("position", "")),
            "matches": int(p["games"]), "minutes": int(p["time"]),
            "goals": f(p, "goals"), "assists": f(p, "assists"),
            "xg": f(p, "xG"), "npxg": f(p, "npxG"), "xa": f(p, "xA"),
            "shots": f(p, "shots"), "key_passes": f(p, "key_passes"),
            "xg_chain": f(p, "xGChain"), "xg_buildup": f(p, "xGBuildup"),
        })
    return pd.DataFrame(rows)


def load(league: str, season: str, raw_dir: Path, refresh: bool = False) -> pd.DataFrame:
    start_year = int(season.split("-")[0])
    cache = raw_dir / f"understat_{league}_{start_year}.json"
    if refresh or not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(fetch_players(league, start_year)), encoding="utf-8")
    return to_rows(json.loads(cache.read_text(encoding="utf-8")), league, season)
