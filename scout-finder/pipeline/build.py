"""Season totals -> per-90 rates -> positional percentiles -> similar players -> JSON.

Usage:
  python -m pipeline.build --fotmob --elo-date 2026-05-31    # the 12-league universe
  python -m pipeline.build --xepl-csv PATH/player_match_stats.csv
  python -m pipeline.build --understat EPL:2025-26
Writes one JSON per season to ../data/.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .league_strength import ADJUSTED

# Metrics compared within each position group. Each is a per-90 rate unless
# listed in RATIOS. A metric is skipped when the source does not publish it,
# so the same profile works for FotMob (wide) and Understat (narrow).
PROFILES = {
    "CB": ["tackles", "interceptions", "clearances", "aerials_won", "passes", "pass_pct",
           "xg_buildup"],
    "FB": ["tackles", "interceptions", "key_passes", "xa", "dribbles", "passes", "touches",
           "xg_chain"],
    "DM": ["tackles", "interceptions", "passes", "pass_pct", "key_passes", "dispossessed",
           "xg_buildup"],
    "CM": ["passes", "pass_pct", "key_passes", "xa", "tackles", "interceptions", "xg",
           "xg_buildup"],
    "AM": ["key_passes", "xa", "xg", "shots", "dribbles", "touches", "dispossessed",
           "xg_chain"],
    "W":  ["xg", "xa", "shots", "key_passes", "dribbles", "touches", "dispossessed",
           "xg_chain"],
    "FW": ["xg", "npxg", "shots", "xg_per_shot", "shots_on_target", "xa", "aerials_won",
           "touches"],
    "GK": ["saves", "passes", "pass_pct"],
}
RATIOS = {
    "pass_pct": ("passes_accurate", "passes"),
    "xg_per_shot": ("xg", "shots"),
}
LOWER_IS_BETTER = {"dispossessed"}
SIMILAR_N = 8


def per90(df: pd.DataFrame) -> pd.DataFrame:
    """Per-90 rates. A stat the source never gave stays NaN (not 0)."""
    out = pd.DataFrame(index=df.index)
    metrics = {m for ms in PROFILES.values() for m in ms}
    for m in metrics:
        if m in RATIOS:
            num, den = RATIOS[m]
            if num in df and den in df:
                out[m] = df[num] / df[den].where(df[den] > 0)
        elif m in df and df[m].notna().any():
            out[m] = df[m] / df["minutes"] * 90
    return out


def min_minutes(minutes: pd.Series) -> int:
    """900 for a finished season; early in a season, 30% of the most-played player's minutes."""
    return int(min(900, 0.3 * minutes.max()))


def percentiles(rates: pd.DataFrame) -> pd.DataFrame:
    pct = rates.rank(pct=True) * 100          # NaN stays NaN
    for m in LOWER_IS_BETTER & set(pct.columns):
        pct[m] = 100 - pct[m] + 100 / rates[m].notna().sum()
    return pct.round(0)


def similar(rates: pd.DataFrame, n: int = SIMILAR_N) -> dict[str, list[tuple[str, float]]]:
    """Cosine similarity on z-scored rates, within one position group.

    z-scoring first means 'similar' compares a player's shape against the group
    average (more tackles than usual, fewer shots than usual), not raw volume.
    A metric a player's league does not publish counts as average (z = 0).
    """
    z = ((rates - rates.mean()) / rates.std(ddof=0).replace(0, 1)).fillna(0)
    v = z.to_numpy()
    v = v / np.linalg.norm(v, axis=1, keepdims=True).clip(min=1e-9)
    sim = v @ v.T
    np.fill_diagonal(sim, -np.inf)
    ids = rates.index.to_list()
    top = np.argsort(-sim, axis=1)[:, :n]
    return {ids[i]: [(ids[j], round(float(sim[i, j]), 3)) for j in top[i]] for i in range(len(ids))}


def _num(x):
    return None if pd.isna(x) else x


def build(season_df: pd.DataFrame, league_factor: dict[str, float] | None = None) -> dict:
    """One season, any number of leagues.

    pct_league: percentile among the same position in the same league.
    pct:        percentile among the same position across the whole universe,
                on strength-adjusted rates (league_strength.py). With one league
                the two are the same.
    similar:    across the whole universe, on adjusted rates.
    """
    league_factor = league_factor or {}
    df = season_df.set_index("player_id")
    # The minutes floor is per league: leagues are at different points of their season.
    floors = df.groupby("league")["minutes"].transform(min_minutes)
    df = df[(df["minutes"] >= floors) & df["pos_group"].notna()]
    raw = per90(df)
    factor = df["league"].map(league_factor).fillna(1.0)
    adj = raw.copy()
    for m in ADJUSTED & set(adj.columns):
        adj[m] = adj[m] * factor

    players, used = [], {}
    for group, profile in PROFILES.items():
        idx = df.index[df["pos_group"] == group]
        # Keep a metric when at least half the group has it (xG is missing in some leagues).
        cols = [m for m in profile if m in raw and raw.loc[idx, m].notna().mean() >= 0.5]
        if len(idx) < 5 or not cols:
            continue
        used[group] = cols
        pct_all = percentiles(adj.loc[idx, cols])
        pct_lg = raw.loc[idx, cols].groupby(df.loc[idx, "league"]).transform(
            lambda s: s.rank(pct=True) * 100).round(0)
        for m in LOWER_IS_BETTER & set(cols):
            pct_lg[m] = (100 - pct_lg[m]).clip(lower=0)
        sims = similar(adj.loc[idx, cols])
        for pid in idx:
            row, p = df.loc[pid], pct_all.loc[pid]
            players.append({
                "id": pid, "name": row["name"], "team": row["team"], "league": row["league"],
                "group": group, "matches": int(row["matches"]), "minutes": int(row["minutes"]),
                "per90": {m: _num(round(float(raw.at[pid, m]), 3)) for m in cols},
                "pct": {m: _num(p[m]) and int(p[m]) for m in cols},
                "pct_league": {m: _num(pct_lg.at[pid, m]) and int(pct_lg.at[pid, m]) for m in cols},
                # The raw material for a numbers-only scouting note.
                "strengths": [m for m in cols if pd.notna(p[m]) and p[m] >= 80],
                "weaknesses": [m for m in cols if pd.notna(p[m]) and p[m] <= 20],
                "similar": [{"id": s, "score": sc} for s, sc in sims[pid]],
            })

    first = season_df.iloc[0]
    leagues = sorted(df["league"].unique())
    return {
        "meta": {"source": first["source"], "season": first["season"], "leagues": leagues,
                 "league_factor": {lg: league_factor.get(lg, 1.0) for lg in leagues},
                 "groups": {g: {"metrics": c, "players": sum(p["group"] == g for p in players)}
                            for g, c in used.items()}},
        "players": players,
    }


def write(season_df: pd.DataFrame, out_dir: Path, name: str,
          league_factor: dict[str, float] | None = None) -> Path:
    data = build(season_df, league_factor)
    path = out_dir / f"{name}_{data['meta']['season']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xepl-csv", type=Path, help="XEPL player_match_stats.csv (FotMob, EPL)")
    ap.add_argument("--fotmob", action="store_true",
                    help="every CSV pipeline.fetch_fotmob wrote under data/fotmob/")
    ap.add_argument("--elo-date", help="YYYY-MM-DD for ClubElo league strength (default: none)")
    ap.add_argument("--understat", action="append", default=[], metavar="LEAGUE:SEASON")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "data")
    ap.add_argument("--refresh", action="store_true", help="re-fetch instead of using data/raw")
    a = ap.parse_args()

    from .sources import fotmob, understat
    factor = None
    if a.elo_date:
        from .league_strength import factors, league_elos
        elos = league_elos(a.elo_date, a.out / "raw")
        factor = factors(elos)
        print("league factors:", factor)
    if a.xepl_csv:
        for _, season_df in fotmob.load_xepl_csv(a.xepl_csv).groupby("season"):
            print("wrote", write(season_df.reset_index(drop=True), a.out, "xepl", factor))
    if a.fotmob:
        paths = sorted((a.out / "fotmob").glob("*.csv"))
        for _, season_df in fotmob.load_fetched(paths).groupby("season"):
            print("wrote", write(season_df.reset_index(drop=True), a.out, "universe", factor))
    for spec in a.understat:
        league, season = spec.split(":")
        df = understat.load(league, season, a.out / "raw", refresh=a.refresh)
        print("wrote", write(df, a.out, f"understat_{league}"))


if __name__ == "__main__":
    main()
