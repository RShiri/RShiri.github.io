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
    "goals": "goals", "assists": "assists", "xg": "xg", "npxg": "npxg", "xa": "xa",
    "xgot": "xgot", "shots": "shots", "sot": "shots_on_target",
    "bigChancesMissed": "big_chances_missed", "keyPasses": "key_passes",
    "bigChancesCreated": "big_chances_created",
    "passes": "passes", "passAcc": "passes_accurate", "finalThirdPasses": "final_third_passes",
    "crosses": "crosses", "crossesAcc": "crosses_accurate",
    "longBalls": "long_balls", "longBallsAcc": "long_balls_accurate",
    "touches": "touches", "boxTouches": "box_touches",
    "dribbles": "dribbles", "dribblesAtt": "dribbles_attempted",
    "dispossessed": "dispossessed", "wasFouled": "was_fouled",
    "tackles": "tackles", "interceptions": "interceptions",
    "tacklesPadj": "tackles_padj", "interceptionsPadj": "interceptions_padj",
    "recoveries": "recoveries", "clearances": "clearances", "blocks": "blocks",
    "dribbledPast": "dribbled_past", "fouls": "fouls",
    "groundDuels": "ground_duels", "groundDuelsWon": "ground_duels_won",
    "aerials": "aerials_won", "aerialsAtt": "aerials",
    "saves": "saves", "savesInsideBox": "saves_inside_box", "goalsConceded": "goals_conceded",
    "xgotFaced": "xgot_faced", "goalsPrevented": "goals_prevented",
    "sweeperActions": "sweeper_actions", "highClaims": "high_claims",
}
# Possession adjustment (PAdj): a defender facing a side that has the ball 65% of
# the time gets more chances to tackle. Each match's count is scaled to what it
# would be at 50% opponent possession.
PADJ = {"tackles": "tacklesPadj", "interceptions": "interceptionsPadj"}


def season_of(date: str) -> str:
    """'2025-08-15' -> '2025-26'. The season turns over on 1 July."""
    y, m = int(date[:4]), int(date[5:7])
    start = y if m >= 7 else y - 1
    return f"{start}-{str(start + 1)[2:]}"


def _main_group(slots: pd.Series) -> str | None:
    """Most-started position. Bench appearances ('Sub' or 'Sub:<coarse slot>') only
    count for players who never started, using FotMob's coarse usual position."""
    groups = slots.map(group_from_slot).dropna()
    if groups.empty:
        subs = slots.dropna().astype(str)
        groups = subs[subs.str.startswith("Sub:")].str[4:].map(group_from_slot).dropna()
    return groups.mode().iat[0] if not groups.empty else None


def _usage(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """How a player was used: starts, rating, share of his team's minutes, positions.

    team_share: minutes / (90 x the matches his last club played in that league-season).
    positions: share of starts per position group, most-played first (top 3).
    """
    pos = df["position"].where(df["position"].notna(), "").astype(str)
    started = (pos != "") & ~pos.str.startswith("Sub")
    g = df.assign(started=started, group=pos.map(group_from_slot)).groupby(keys)
    out = pd.DataFrame({"starts": g["started"].sum().astype(int)})
    if "rating" in df:
        w = df.assign(rw=df["rating"] * df["minutes"],
                      rm=df["minutes"].where(df["rating"].notna()))
        rg = w.groupby(keys)
        out["rating"] = (rg["rw"].sum(min_count=1) / rg["rm"].sum()).round(2)
    team_games = df.groupby(["league", "season", "team"])["match_id"].nunique()
    last_team = g["team"].last()
    games = pd.Series([team_games.get((lg, se, t)) for (lg, se, _), t in last_team.items()],
                      index=last_team.index)
    out["team_share"] = (g["minutes"].sum() / (90 * games)).clip(upper=1).round(2)
    starts = df[started].assign(group=pos[started].map(group_from_slot)).dropna(subset=["group"])
    shares = starts.groupby(keys)["group"].value_counts(normalize=True).round(2)
    out["positions"] = pd.Series({k: dict(list(v.droplevel(keys).items())[:3])
                                  for k, v in shares.groupby(level=keys)}, dtype=object)
    return out


def from_match_rows(df: pd.DataFrame, league: str = "ENG1") -> pd.DataFrame:
    df = df.copy()
    if "season" not in df:
        df["season"] = df["date"].astype(str).map(season_of)
    df = df.sort_values("date")
    if "oppPossession" in df:
        scale = 50 / df["oppPossession"].where(df["oppPossession"] > 0)
        for raw, adj in PADJ.items():
            if raw in df:
                df[adj] = df[raw] * scale
    if "league" not in df:
        df["league"] = league
    keys = ["league", "season", "player_id"]
    cols = [c for c in SUM_COLS if c in df]
    # min_count=1: a stat FotMob never gave for this player stays NaN instead of 0,
    # so a league without xG is "no xG data", not "zero xG".
    totals = df.groupby(keys)[cols].sum(min_count=1).rename(columns=SUM_COLS)
    info = df.groupby(keys).agg(
        name=("player", "last"),
        team=("team", "last"),          # club at the end of the season
        matches=("match_id", "nunique"),
        minutes=("minutes", "sum"),
        pos_group=("position", _main_group),
    )
    # Age, market value and nationality: the latest the lineups gave this season.
    for col, out_col in (("age", "age"), ("valueEur", "value_eur"), ("country", "country")):
        if col in df:
            info[out_col] = df.dropna(subset=[col]).groupby(keys)[col].last()
    info = info.join(_usage(df, keys))
    out = info.join(totals).reset_index()
    out["source"] = "fotmob"
    out["player_id"] = "fotmob:" + out["player_id"].astype(str)
    # A player who moved between leagues mid-season keeps one entry per league (so
    # league percentiles stay within a league); those stints get "@<league>".
    multi = out.duplicated(["season", "player_id"], keep=False)
    out.loc[multi, "player_id"] += "@" + out.loc[multi, "league"]
    return out


def load_xepl_csv(path: Path, league: str = "ENG1") -> pd.DataFrame:
    return from_match_rows(pd.read_csv(path), league)


def load_fetched(paths: list[Path]) -> pd.DataFrame:
    """CSVs written by pipeline.fetch_fotmob (they carry their own league column)."""
    return from_match_rows(pd.concat([pd.read_csv(p) for p in paths], ignore_index=True))
