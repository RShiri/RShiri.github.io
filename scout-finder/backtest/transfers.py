"""From raw matches to one row per player per season pair: moved, stayed or gone.

  python -m backtest.transfers          # train pair only, writes data/transfers.csv
  python -m backtest.transfers --test   # adds 2025-26 -> 2026-27 (run at the season's end)

The definitions are Ram's, with the reasons in BACKTEST.md:
  moved:   most-minutes club in t != most-minutes club in t+1
  success: at least half of the new club's minutes from his first appearance there
  gone:    in t, in none of the 12 leagues in t+1; kept out of the model, but counted
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .options import player_clubs

DATA = Path(__file__).resolve().parent.parent / "data"
TRAIN = ("2024-25", "2025-26")
TEST = ("2025-26", "2026-27")
SUCCESS_SHARE = 0.5
COLS = ["league", "season", "match_id", "date", "team", "teamId", "player_id", "minutes"]


def clubs_with_debut_share(raw: pd.DataFrame) -> pd.DataFrame:
    """player_clubs, plus his share of the club's minutes from his first appearance on."""
    pc = player_clubs(raw)
    played = raw[raw["minutes"] > 0].drop_duplicates(["league", "season", "teamId", "match_id"])
    dates = {k: np.sort(g.to_numpy()) for k, g in played.groupby(["league", "season", "teamId"])["date"]}
    pc["games_since"] = [len(dates[k]) - np.searchsorted(dates[k], first) for k, first in
                         zip(zip(pc["league"], pc["season"], pc["teamId"]), pc["first"])]
    pc["share_since"] = (pc["minutes"] / (90 * pc["games_since"])).clip(upper=1)
    return pc


def main_club(pc: pd.DataFrame) -> pd.DataFrame:
    """The player's most-minutes club in a season; teamId breaks a tie the same way every run."""
    return pc.sort_values(["minutes", "teamId"]).groupby("player_id").last()


def transfers(pc: pd.DataFrame, t: str, t1: str) -> pd.DataFrame:
    prev = main_club(pc[pc["season"] == t])
    new = main_club(pc[pc["season"] == t1])
    out = pd.DataFrame({"season_t": t, "season_t1": t1, "prev_team": prev["team"],
                        "prev_team_id": prev["teamId"], "prev_league": prev["league"],
                        "prev_minutes": prev["minutes"], "prev_share": prev["share_since"]})
    out = out.join(new[["team", "teamId", "league", "minutes", "games_since", "share_since", "share"]].rename(
        columns={"team": "new_team", "teamId": "new_team_id", "league": "new_league", "minutes": "new_minutes",
                 "games_since": "new_games_since", "share_since": "new_share_since", "share": "new_share_season"}))
    out["status"] = np.select([out["new_team_id"].isna(), out["new_team_id"] == out["prev_team_id"]],
                              ["gone", "stayed"], "moved")
    # Only a move can succeed or fail; NaN for the rest, so a mean never counts them.
    out["success"] = (out["new_share_since"] >= SUCCESS_SHARE).astype(float).where(out["status"] == "moved")
    return out.reset_index()


def with_features(table: pd.DataFrame, stints: pd.DataFrame, universes: dict[str, dict]) -> pd.DataFrame:
    """Add what was known in season t. Nothing here may come from t+1 except the destination."""
    t_rows = stints.rename(columns={"season": "season_t", "league": "prev_league"})[
        ["player_id", "season_t", "prev_league", "name", "age", "value_eur", "rating", "pos_group"]]
    out = table.assign(player_id="fotmob:" + table["player_id"].astype(str)).merge(
        t_rows, on=["player_id", "season_t", "prev_league"], how="left")
    scores = {(p["id"].split("@")[0], p["league"], season): p["score"]
              for season, u in universes.items() for p in u["players"]}
    out["score"] = [scores.get(k) for k in zip(out["player_id"], out["prev_league"], out["season_t"])]
    # One Elo snapshot (2026-10-13) for every pair: see the limits in BACKTEST.md.
    factor = universes["2025-26"]["meta"]["league_factor"]
    out["league_gap"] = np.log(out["new_league"].map(factor)) - np.log(out["prev_league"].map(factor))
    return out


def load_raw() -> pd.DataFrame:
    paths = [p for p in sorted((DATA / "fotmob").glob("*.csv")) if p.stat().st_size > 1000]
    if not paths:
        raise SystemExit("no match CSVs in data/fotmob/")
    return pd.concat([pd.read_csv(p, usecols=COLS) for p in paths])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="also build the test pair")
    a = ap.parse_args()
    pairs = [TRAIN, TEST] if a.test else [TRAIN]
    pc = clubs_with_debut_share(load_raw())
    stints = pd.read_csv(DATA / "stints.csv")
    seasons = {t for t, _ in pairs} | {"2025-26"}  # 2025-26 carries the 12-league factors
    universes = {s: json.loads((DATA / f"universe_{s}.json").read_text(encoding="utf-8")) for s in seasons}
    out = pd.concat([with_features(transfers(pc, t, t1), stints, universes) for t, t1 in pairs])
    out.to_csv(DATA / "transfers.csv", index=False, float_format="%.4g")
    print(out.groupby(["season_t", "status"]).size().unstack(fill_value=0).to_string())
    print("success rate:", out.groupby("season_t")["success"].mean().round(3).to_dict())


if __name__ == "__main__":
    main()
