"""Season totals -> per-90 rates -> positional percentiles -> similar players -> JSON.

Usage:
  python -m pipeline.build --xepl-csv PATH/player_match_stats.csv
  python -m pipeline.build --understat EPL:2025-26 --understat LaLiga:2025-26
Writes one JSON per (source, league, season) to ../data/.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

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
    out = pd.DataFrame(index=df.index)
    metrics = {m for ms in PROFILES.values() for m in ms}
    for m in metrics:
        if m in RATIOS:
            num, den = RATIOS[m]
            if num in df and den in df:
                out[m] = (df[num] / df[den].replace(0, np.nan)).fillna(0)
        elif m in df and df[m].notna().any():
            out[m] = df[m] / df["minutes"] * 90
    return out


def min_minutes(df: pd.DataFrame) -> int:
    """900 for a finished season; early in a season, 30% of the most-played player's minutes."""
    return int(min(900, 0.3 * df["minutes"].max()))


def percentiles(rates: pd.DataFrame) -> pd.DataFrame:
    pct = rates.rank(pct=True) * 100
    for m in LOWER_IS_BETTER & set(pct.columns):
        pct[m] = 100 - pct[m] + 100 / len(pct)
    return pct.round(0)


def similar(rates: pd.DataFrame, n: int = SIMILAR_N) -> dict[str, list[tuple[str, float]]]:
    """Cosine similarity on z-scored rates, within one position group.

    z-scoring first means 'similar' compares a player's shape against the group
    average (more tackles than usual, fewer shots than usual), not raw volume.
    """
    z = (rates - rates.mean()) / rates.std(ddof=0).replace(0, 1)
    v = z.to_numpy()
    v = v / np.linalg.norm(v, axis=1, keepdims=True).clip(min=1e-9)
    sim = v @ v.T
    np.fill_diagonal(sim, -np.inf)
    ids = rates.index.to_list()
    top = np.argsort(-sim, axis=1)[:, :n]
    return {ids[i]: [(ids[j], round(float(sim[i, j]), 3)) for j in top[i]] for i in range(len(ids))}


def build(season_df: pd.DataFrame) -> dict:
    df = season_df.set_index("player_id")
    floor = min_minutes(df)
    df = df[(df["minutes"] >= floor) & df["pos_group"].notna()]
    rates_all = per90(df)

    players, used = [], {}
    for group, profile in PROFILES.items():
        idx = df.index[df["pos_group"] == group]
        cols = [m for m in profile if m in rates_all]
        if len(idx) < 5 or not cols:
            continue
        used[group] = cols
        rates = rates_all.loc[idx, cols]
        pct = percentiles(rates)
        sims = similar(rates)
        for pid in idx:
            row = df.loc[pid]
            p = pct.loc[pid]
            players.append({
                "id": pid, "name": row["name"], "team": row["team"], "group": group,
                "matches": int(row["matches"]), "minutes": int(row["minutes"]),
                "per90": {m: round(float(rates.at[pid, m]), 3) for m in cols},
                "pct": {m: int(p[m]) for m in cols},
                # The raw material for a numbers-only scouting note.
                "strengths": [m for m in cols if p[m] >= 80],
                "weaknesses": [m for m in cols if p[m] <= 20],
                "similar": [{"id": s, "score": sc} for s, sc in sims[pid]],
            })

    first = season_df.iloc[0]
    return {
        "meta": {"source": first["source"], "league": first["league"],
                 "season": first["season"], "min_minutes": floor,
                 "groups": {g: {"metrics": c, "players": sum(p["group"] == g for p in players)}
                            for g, c in used.items()}},
        "players": players,
    }


def write(season_df: pd.DataFrame, out_dir: Path) -> Path:
    data = build(season_df)
    m = data["meta"]
    path = out_dir / f"{m['source']}_{m['league']}_{m['season']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xepl-csv", type=Path, help="XEPL player_match_stats.csv (FotMob)")
    ap.add_argument("--understat", action="append", default=[], metavar="LEAGUE:SEASON")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "data")
    ap.add_argument("--refresh", action="store_true", help="re-fetch instead of using data/raw")
    a = ap.parse_args()

    from .sources import fotmob, understat
    if a.xepl_csv:
        for _, season_df in fotmob.load_xepl_csv(a.xepl_csv).groupby("season"):
            print("wrote", write(season_df.reset_index(drop=True), a.out))
    for spec in a.understat:
        league, season = spec.split(":")
        df = understat.load(league, season, a.out / "raw", refresh=a.refresh)
        print("wrote", write(df, a.out))


if __name__ == "__main__":
    main()
