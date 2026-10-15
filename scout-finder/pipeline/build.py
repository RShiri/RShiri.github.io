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
    "CB": ["tackles_padj", "interceptions_padj", "clearances", "blocks", "aerials_won",
           "aerial_pct", "ground_duel_pct", "passes", "pass_pct", "long_balls_accurate",
           "xg_buildup"],
    "FB": ["tackles_padj", "interceptions_padj", "recoveries", "ground_duel_pct",
           "crosses_accurate", "key_passes", "xa", "final_third_passes", "dribbles", "touches",
           "xg_chain"],
    "DM": ["tackles_padj", "interceptions_padj", "recoveries", "ground_duel_pct", "passes",
           "pass_pct", "long_balls_accurate", "final_third_passes", "dispossessed",
           "xg_buildup"],
    "CM": ["passes", "pass_pct", "final_third_passes", "key_passes", "xa", "xg",
           "box_touches", "tackles_padj", "interceptions_padj", "recoveries", "xg_buildup"],
    "AM": ["key_passes", "big_chances_created", "xa", "xg", "shots", "box_touches",
           "dribbles", "dribble_pct", "final_third_passes", "dispossessed", "xg_chain"],
    "W":  ["xg", "xa", "shots", "key_passes", "big_chances_created", "dribbles", "dribble_pct",
           "crosses_accurate", "box_touches", "dispossessed", "xg_chain"],
    "FW": ["xg", "npxg", "shots", "xg_per_shot", "shots_on_target", "xa", "box_touches",
           "aerials_won", "aerial_pct"],
    "GK": ["save_pct", "goals_prevented", "saves_inside_box", "sweeper_actions",
           "high_claims", "passes", "pass_pct", "long_balls_accurate"],
}
RATIOS = {
    "pass_pct": ("passes_accurate", "passes"),
    "xg_per_shot": ("xg", "shots"),
    "aerial_pct": ("aerials_won", "aerials"),
    "ground_duel_pct": ("ground_duels_won", "ground_duels"),
    "dribble_pct": ("dribbles", "dribbles_attempted"),
    "save_pct": ("saves", "shots_faced"),
}
LOWER_IS_BETTER = {"dispossessed"}
# A ratio built on a handful of attempts is noise (2 of 2 aerials is not 100%).
# Below this many attempts per 90 over the season the ratio stays empty.
MIN_ATTEMPTS_P90 = {"aerial_pct": 1.0, "ground_duel_pct": 1.5, "dribble_pct": 0.5,
                    "xg_per_shot": 0.5}
PROFILE_FIELDS = ["team_id", "age", "value_eur", "country", "height", "foot", "contract_end",
                  "birth_date", "current_team", "main_position",
                  "starts", "rating", "team_share", "positions"]
# Season totals shown next to the per-90s (volume matters too).
TOTALS = ["goals", "assists", "xg", "xa", "shots", "key_passes"]


def attach_profiles(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Merge pipeline.fetch_players output (FotMob's profile as of the fetch day).

    Profile value_eur is today's; it replaces the in-season lineup value when present.
    """
    if not path.exists():
        return df
    profiles = json.loads(path.read_text(encoding="utf-8"))
    fid = df["player_id"].str.extract(r"^fotmob:(\d+)")[0]
    prof = pd.DataFrame([profiles.get(i, {}) if isinstance(i, str) else {} for i in fid],
                        index=df.index)
    df = df.copy()
    for col in prof.columns:
        df[col] = prof[col].combine_first(df[col]) if col in df else prof[col]
    return df
SIMILAR_N = 8


# DM vs CM. FotMob's lineup slots cannot tell a 6 from an 8 (PROGRESS.md), so the
# split is by the shape of a central midfielder's numbers: a 6 wins the ball back
# and circulates it, and rarely arrives in the box or creates. Score = mean z of
# DM_PLUS minus mean z of DM_MINUS, z within the season's CM pool; above the
# threshold is DM. Checked on 30 well-known midfielders (about 80% agree with the
# usual label); deep-lying playmakers (Kimmich, Paredes) mostly stay CM.
DM_PLUS = ["interceptions_padj", "recoveries", "passes"]
DM_MINUS = ["box_touches", "xa", "key_passes"]
DM_THRESHOLD = 0.25


def dm_score(rates: pd.DataFrame) -> pd.Series:
    def z(c):
        if c not in rates:
            return pd.Series(0.0, index=rates.index)
        return ((rates[c] - rates[c].mean()) / rates[c].std(ddof=0)).fillna(0)
    return (sum(z(c) for c in DM_PLUS) / len(DM_PLUS)
            - sum(z(c) for c in DM_MINUS) / len(DM_MINUS))


def per90(df: pd.DataFrame) -> pd.DataFrame:
    """Per-90 rates. A stat the source never gave stays NaN (not 0)."""
    out = pd.DataFrame(index=df.index)
    metrics = {m for ms in PROFILES.values() for m in ms}
    for m in metrics:
        if m in RATIOS:
            num, den = RATIOS[m]
            if den == "shots_faced" and "saves" in df and "goals_conceded" in df:
                df = df.assign(shots_faced=df["saves"] + df["goals_conceded"])
            if num in df and den in df:
                floor = MIN_ATTEMPTS_P90.get(m, 0) * df["minutes"] / 90
                out[m] = df[num] / df[den].where((df[den] > 0) & (df[den] >= floor))
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


def _extras(row: pd.Series) -> dict:
    """Per-90 stats only some leagues have (progressive passes / carries, xT)."""
    out = {f"{c}_p90": round(float(row[c]) / row["minutes"] * 90, 2)
           for c in EXTRA_P90 if c in row and pd.notna(row[c]) and row["minutes"]}
    if "xt_added_p90" in row and pd.notna(row["xt_added_p90"]):
        out["xt_added_p90"] = round(float(row["xt_added_p90"]), 3)
    return {"extras": out} if out else {}


def _present(x) -> bool:
    return isinstance(x, dict) and bool(x) or not isinstance(x, dict) and pd.notna(x)


def _plain(x):
    """numpy scalars -> JSON-friendly Python values (ages and values as ints)."""
    if isinstance(x, (np.integer, np.floating)):
        return int(x) if float(x).is_integer() else round(float(x), 1)
    return x


def _num(x):
    return None if pd.isna(x) else x


EXTRA_P90 = ["prog_passes", "prog_carries"]   # only where Ram's XEPL/XLALIGA data exists


def build(season_df: pd.DataFrame, league_factor: dict[str, float] | None = None,
          meta: dict | None = None) -> dict:
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
    cm = df.index[df["pos_group"] == "CM"]
    if len(cm) >= 10 and all(m in raw for m in DM_PLUS + DM_MINUS):
        df = df.copy()
        df.loc[cm[(dm_score(raw.loc[cm]) > DM_THRESHOLD).to_numpy()], "pos_group"] = "DM"
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
            # Skipping a group drops its players from the file: say so (PROGRESS.md, Rodri).
            if len(idx):
                print(f"WARNING: group {group} skipped ({len(idx)} players, metrics {cols})"
                      f" - its players are not in the output")
            continue
        used[group] = cols
        pct_all = percentiles(adj.loc[idx, cols])
        # Overall level inside the group: mean of the universe percentiles (only the
        # metrics the player's league publishes), ranked again so it spreads 0-100.
        level = (pct_all.mean(axis=1).rank(pct=True) * 100).round(0)
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
                **{f: _plain(row[f]) for f in PROFILE_FIELDS if f in row and _present(row[f])},
                "totals": {c: _plain(round(float(row[c]), 2)) for c in TOTALS
                           if c in row and pd.notna(row[c])},
                **_extras(row),
                "per90": {m: _num(round(float(raw.at[pid, m]), 3)) for m in cols},
                "score": _num(level.at[pid]) and int(level.at[pid]),
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
                 # FotMob's image CDN: {id} = numeric FotMob player id, {team_id} = club id.
                 "images": {
                     "player": "https://images.fotmob.com/image_resources/playerimages/{id}.png",
                     "crest": "https://images.fotmob.com/image_resources/logo/teamlogo/{team_id}.png",
                 },
                 "score_note": ("score = overall level inside the position group (mean of the "
                                "universe percentiles, re-ranked 0-100). Solid for attackers; "
                                "for CB and GK it leans on defending volume and one season of "
                                "goals prevented, so treat it as a profile, not a ranking."),
                 **(meta or {}),
                 "groups": {g: {"metrics": c, "players": sum(p["group"] == g for p in players)}
                            for g, c in used.items()}},
        "players": players,
    }


def write(season_df: pd.DataFrame, out_dir: Path, name: str,
          league_factor: dict[str, float] | None = None, meta: dict | None = None) -> Path:
    data = build(season_df, league_factor, meta)
    path = out_dir / f"{name}_{data['meta']['season']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return path


def write_season_index(out_dir: Path, default: str | None = None) -> Path:
    """data/seasons.json: the built universe seasons, newest first, and which to open.

    The default is the newest season that has run most of its course (its busiest
    player has 80% of the minutes the busiest player of any season has): early in
    a season the minutes floor drops, so player counts alone would pick it.
    """
    seasons = sorted((p.stem.split("_", 1)[1] for p in out_dir.glob("universe_*.json")),
                     reverse=True)
    if default is None:
        played = {s: max(p["minutes"] for p in json.loads((out_dir / f"universe_{s}.json")
                                                          .read_text(encoding="utf-8"))["players"])
                  for s in seasons}
        full = [s for s in seasons if played[s] >= 0.8 * max(played.values())]
        default = full[0] if full else (seasons[0] if seasons else None)
    path = out_dir / "seasons.json"
    path.write_text(json.dumps({"seasons": seasons, "default": default}), encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xepl-csv", type=Path, help="XEPL player_match_stats.csv (FotMob, EPL)")
    ap.add_argument("--fotmob", action="store_true",
                    help="every CSV pipeline.fetch_fotmob wrote under data/fotmob/")
    ap.add_argument("--season", action="append", default=[],
                    help="with --fotmob: only these seasons (default: every CSV found)")
    ap.add_argument("--no-ram-xg", action="store_true",
                    help="keep FotMob's xG in the EPL and LaLiga (default: Ram's model)")
    ap.add_argument("--elo-date", help="YYYY-MM-DD for ClubElo league strength (default: none)")
    ap.add_argument("--understat", action="append", default=[], metavar="LEAGUE:SEASON")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "data")
    ap.add_argument("--refresh", action="store_true", help="re-fetch instead of using data/raw")
    a = ap.parse_args()

    from .sources import fotmob, understat
    factor, beta_fit = None, None
    if a.elo_date:
        from .league_strength import factors, fitted_beta, league_elos
        elos = league_elos(a.elo_date, a.out / "raw")
        beta, beta_fit = fitted_beta(a.out / "beta_fit.json")
        factor = factors(elos, beta)
        print(f"league factors (beta {beta}):", factor)
    if a.xepl_csv:
        for _, season_df in fotmob.load_xepl_csv(a.xepl_csv).groupby("season"):
            print("wrote", write(season_df.reset_index(drop=True), a.out, "xepl", factor))
    if a.fotmob:
        paths = sorted(p for p in (a.out / "fotmob").glob("*.csv")
                       if not a.season or p.stem.split("_", 1)[1] in a.season)
        from .sources import ram_xg
        universe = attach_profiles(fotmob.load_fetched(paths), a.out / "players.json")
        if not a.no_ram_xg:
            universe, _, xg_scale = ram_xg.apply(universe)
            print("Ram's xG model, scale to FotMob level:", xg_scale)
        for season, season_df in universe.groupby("season"):
            meta = {"beta_fit": beta_fit} if beta_fit else {}
            if not a.no_ram_xg:
                meta["xg_source"] = {lg: "ram" if any(k.startswith(f"{lg} {season} ") for k in xg_scale)
                                     else "fotmob" for lg in sorted(season_df["league"].unique())}
                meta["xg_scale"] = {k.split(" ", 2)[0] + " " + k.split(" ", 2)[2]: v
                                    for k, v in xg_scale.items() if f" {season} " in k}
            print("wrote", write(season_df.reset_index(drop=True), a.out, "universe", factor, meta))
        write_season_index(a.out)
    for spec in a.understat:
        league, season = spec.split(":")
        df = understat.load(league, season, a.out / "raw", refresh=a.refresh)
        print("wrote", write(df, a.out, f"understat_{league}"))


if __name__ == "__main__":
    main()
