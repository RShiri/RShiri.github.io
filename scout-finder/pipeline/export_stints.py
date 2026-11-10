"""Every player-league-season, with no minutes floor, for the transfer back-test.

  python -m pipeline.export_stints        # writes data/stints.csv

The universe files keep players with ~900+ minutes, so a signing who barely played
after his move is missing from them, and those are exactly the failed transfers.
This file keeps everyone FotMob saw play, with the usage columns (club, minutes,
starts, share of the club's minutes, rating) plus season totals, so the back-test
can see who moved and how much they played afterwards. Needs the raw match CSVs
in data/fotmob/ (Ram's PC).
"""
from __future__ import annotations

from pathlib import Path

from .sources import fotmob

DATA = Path(__file__).resolve().parent.parent / "data"
USAGE = ["player_id", "name", "league", "season", "team", "team_id", "pos_group",
         "matches", "minutes", "starts", "team_share", "rating", "age", "value_eur"]


def stints(season_rows):
    """Season totals (from fotmob.from_match_rows) -> one tidy row per stint."""
    df = season_rows.copy()
    df["player_id"] = df["player_id"].str.extract(r"^(fotmob:\d+)")[0]
    totals = [c for c in fotmob.SUM_COLS.values() if c in df]
    cols = [c for c in USAGE if c in df] + totals
    return df[cols].sort_values(["player_id", "season", "league"]).reset_index(drop=True)


def main() -> None:
    paths = sorted((DATA / "fotmob").glob("*.csv"))
    if not paths:
        raise SystemExit("no match CSVs in data/fotmob/ - run pipeline.fetch_fotmob first")
    out = stints(fotmob.load_fetched(paths))
    out.to_csv(DATA / "stints.csv", index=False, float_format="%.4g")
    print(f"{len(out)} stints, {out['player_id'].nunique()} players")
    print(out.groupby(["season", "league"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
