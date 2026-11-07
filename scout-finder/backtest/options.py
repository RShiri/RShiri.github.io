"""How much each open decision in BACKTEST.md moves the numbers. Decides nothing.

  python backtest/options.py

Works from the raw match CSVs (data/fotmob/, Ram's PC) at player x club level, not
from stints.csv: a player who changed clubs inside one league is a single stint row,
and the back-test needs to see both clubs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
THRESHOLDS = (0.3, 0.5, 0.7)


def player_clubs(raw: pd.DataFrame) -> pd.DataFrame:
    """One row per player x club x season, with the share of that club's league minutes."""
    raw = raw[raw["minutes"] > 0]
    club_games = raw.groupby(["league", "season", "teamId"])["match_id"].nunique().rename("club_games")
    pc = (raw.groupby(["player_id", "season", "league", "teamId"])
             .agg(team=("team", "last"), minutes=("minutes", "sum"),
                  first=("date", "min"), last=("date", "max"))
             .join(club_games).reset_index())
    pc["share"] = (pc["minutes"] / (90 * pc["club_games"])).clip(upper=1)
    return pc


def season_pair(pc: pd.DataFrame, t: str, t1: str, min_minutes: int = 0) -> dict:
    a, b = pc[pc["season"] == t], pc[pc["season"] == t1]
    if t == "2024-25":
        a = a[a["league"] != "ISR1"]  # no ISR1 player data for 2024-25
    total = a.groupby("player_id")["minutes"].sum()
    pool = total[total >= min_minutes].index
    end_club = a.sort_values("last").groupby("player_id")["teamId"].last()
    most_t = a.sort_values("minutes").groupby("player_id")["teamId"].last()
    main_t1 = b.sort_values("minutes").groupby("player_id").last()
    first_t1 = b.sort_values("first").groupby("player_id")["teamId"].first()
    clubs_t1 = b.groupby("player_id")["teamId"].nunique()
    present = pool.intersection(main_t1.index)
    moved = {
        "A: club at end of t != most-minutes club in t+1": end_club[present] != main_t1["teamId"][present],
        "B: club at end of t != first club in t+1": end_club[present] != first_t1[present],
        "C: most-minutes club in t != most-minutes club in t+1": most_t[present] != main_t1["teamId"][present],
    }
    out = {"pool": len(pool), "gone": len(pool) - len(present), "defs": {}}
    for name, mask in moved.items():
        ids = mask[mask].index
        share = main_t1.loc[ids, "share"]
        out["defs"][name] = {"n": len(ids), **{th: (share >= th).mean() for th in THRESHOLDS},
                             "two_clubs_t1": int((clubs_t1[ids] > 1).sum())}
    stay = present.difference(moved["A: club at end of t != most-minutes club in t+1"].pipe(lambda m: m[m].index))
    out["stayers"] = (len(stay), (main_t1.loc[stay, "share"] >= 0.5).mean())
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cols = ["league", "season", "match_id", "date", "team", "teamId", "player_id", "minutes"]
    paths = sorted((DATA / "fotmob").glob("*.csv"))
    if not paths:
        raise SystemExit("no match CSVs in data/fotmob/")
    raw = pd.concat([pd.read_csv(p, usecols=cols) for p in paths if p.stat().st_size > 1000])
    pc = player_clubs(raw)

    print("last match date per season:", raw.groupby("season")["date"].max().to_dict())
    games = pc.drop_duplicates(["league", "season", "teamId"]).query("season == '2026-27'")
    print("median club games in 2026-27:", games.groupby("league")["club_games"].median().to_dict())

    clubs = pc.groupby(["player_id", "season"])["teamId"].nunique()
    same = pc.groupby(["player_id", "season", "league"])["teamId"].nunique()
    print("players with 2+ clubs in a season:", (clubs > 1).groupby("season").sum().to_dict())
    print("  2 clubs in the same league (one stint row):", (same > 1).groupby("season").sum().to_dict())

    for floor in (0, 900):
        for t, t1 in (("2024-25", "2025-26"), ("2025-26", "2026-27")):
            r = season_pair(pc, t, t1, floor)
            print(f"\n{t} -> {t1}, >= {floor} min in t: {r['pool']} players, "
                  f"gone from all 12 leagues {r['gone']} ({r['gone'] / r['pool']:.0%})")
            for name, d in r["defs"].items():
                rates = "  ".join(f"share>={th}: {d[th]:.0%}" for th in THRESHOLDS)
                print(f"  {name}: {d['n']} moves | {rates} | 2+ clubs in t+1: {d['two_clubs_t1']}")
            print(f"  stayers (def A) with share>=0.5 in t+1: {r['stayers'][1]:.0%} (n={r['stayers'][0]})")

    # stints.csv sums both clubs' minutes but divides by the last club's games.
    st = pd.read_csv(DATA / "stints.csv")
    movers = same[same > 1].reset_index()[["player_id", "season", "league"]]
    last = pc.sort_values("last").groupby(["player_id", "season", "league"]).last().reset_index()
    j = movers.merge(last, on=["player_id", "season", "league"])
    j["player_id"] = "fotmob:" + j["player_id"].astype(str)
    j = j.merge(st[["player_id", "season", "league", "team_share"]], on=["player_id", "season", "league"])
    for season, g in j.groupby("season"):
        print(f"\nsame-league movers {season}: n={len(g)}, stints team_share {g['team_share'].mean():.2f} "
              f"vs last club only {g['share'].mean():.2f}, off by >= 0.1 in {(g['team_share'] - g['share'] >= 0.1).sum()}")


if __name__ == "__main__":
    main()
