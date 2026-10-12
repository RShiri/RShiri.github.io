"""FotMob: the current season (and last season, for the EPL), from per-match player stats.

FotMob has no single "every player's season totals" endpoint; its league stat
pages only list the top N per stat. So we sum per-match player stats instead.

XEPL already scrapes FotMob matchDetails after every EPL matchday (curl_cffi,
/api/data/matchDetails) and writes one row per player per match to
epl_dashboard/database/player_match_stats.csv. Scout Finder reads that file
rather than scraping FotMob a second time: one scraper to keep alive, not two.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..positions import group_from_slot

# XEPL column -> schema column. Everything here is summed over the season.
SUM_COLS = {
    "goals": "goals", "assists": "assists", "xg": "xg", "xa": "xa",
    "shots": "shots", "sot": "shots_on_target", "keyPasses": "key_passes",
    "passes": "passes", "passAcc": "passes_accurate", "touches": "touches",
    "dribbles": "dribbles", "tackles": "tackles", "interceptions": "interceptions",
    "clearances": "clearances", "aerials": "aerials_won",
    "dispossessed": "dispossessed", "saves": "saves",
}


def season_of(date: str) -> str:
    """'2025-08-15' -> '2025-26'. The season turns over on 1 July."""
    y, m = int(date[:4]), int(date[5:7])
    start = y if m >= 7 else y - 1
    return f"{start}-{str(start + 1)[2:]}"


def _main_group(slots: pd.Series) -> str | None:
    """Most-started position. Bench appearances ('Sub') carry no position."""
    groups = slots.map(group_from_slot).dropna()
    return groups.mode().iat[0] if not groups.empty else None


def from_match_rows(df: pd.DataFrame, league: str = "EPL") -> pd.DataFrame:
    df = df.copy()
    df["season"] = df["date"].astype(str).map(season_of)
    df = df.sort_values("date")
    keys = ["season", "player_id"]
    totals = df.groupby(keys)[list(SUM_COLS)].sum().rename(columns=SUM_COLS)
    info = df.groupby(keys).agg(
        name=("player", "last"),
        team=("team", "last"),          # club at the end of the season
        matches=("match_id", "nunique"),
        minutes=("minutes", "sum"),
        pos_group=("position", _main_group),
    )
    out = info.join(totals).reset_index()
    out["source"] = "fotmob"
    out["league"] = league
    out["player_id"] = "fotmob:" + out["player_id"].astype(str)
    return out


def load_xepl_csv(path: Path, league: str = "EPL") -> pd.DataFrame:
    return from_match_rows(pd.read_csv(path), league)
