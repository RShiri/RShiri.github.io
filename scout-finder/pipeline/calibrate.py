"""Fit the league-strength BETA on players who changed leagues.

  python -m pipeline.calibrate --elo-date 2026-05-31     # writes data/beta_fit.json

league_strength scales attacking per-90s by exp(BETA * (league_elo - ref) / 100).
If that is right, a player who moves from league A to league B keeps the same
adjusted output, so his raw rates change by

    log(rate_B / rate_A) = BETA * (elo_A - elo_B) / 100

Each mover gives one point: x = (elo_A - elo_B) / 100, y = the mean log ratio of
his attacking per-90s (shots, key passes, box touches, dribbles, xG and xA when
both leagues publish them). BETA is the weighted least-squares slope through
the origin, weighted by the smaller of the two stints' minutes; the 90% interval
comes from resampling the movers (bootstrap).

Movers: the same FotMob player in two leagues within one season (a January
move), or in consecutive seasons. Known bias: a player who moves up usually
joins a bigger club in a bigger role, and one who moves down is often past his
best, so the fit is a rough guide, not a law.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .league_strength import league_elos
from .sources import fotmob

DATA = Path(__file__).resolve().parent.parent / "data"
METRICS = ["shots", "key_passes", "box_touches", "dribbles", "xg", "xa"]
MIN_STINT = 450        # minutes in each league
EPS = 0.05             # per-90 floor, so a zero does not make the log ratio infinite


def stints(df: pd.DataFrame) -> pd.DataFrame:
    """Season totals -> one row per player-league-season with per-90 rates."""
    out = df[df["minutes"] >= MIN_STINT].copy()
    out["base_id"] = out["player_id"].str.extract(r"^(fotmob:\d+)")[0]
    for m in METRICS:
        if m in out:
            out[f"{m}_p90"] = out[m] / out["minutes"] * 90
    return out


def season_index(season: str) -> int:
    return int(season[:4])


def movers(st: pd.DataFrame, elo: dict[str, float]) -> pd.DataFrame:
    """Pairs of stints of one player in two leagues: same season or consecutive."""
    rows = []
    for _, g in st.groupby("base_id"):
        if g["league"].nunique() < 2:
            continue
        recs = g.to_dict("records")
        for i, a in enumerate(recs):
            for b in recs[i + 1:]:
                if a["league"] == b["league"]:
                    continue
                gap = abs(season_index(a["season"]) - season_index(b["season"]))
                if gap > 1 or a["league"] not in elo or b["league"] not in elo:
                    continue
                if season_index(b["season"]) < season_index(a["season"]):
                    a, b = b, a
                logs = [np.log((b[f"{m}_p90"] + EPS) / (a[f"{m}_p90"] + EPS)) for m in METRICS
                        if pd.notna(a.get(f"{m}_p90")) and pd.notna(b.get(f"{m}_p90"))]
                if len(logs) < 3:
                    continue
                rows.append({"player": b["name"], "from": a["league"], "to": b["league"],
                             "from_season": a["season"], "to_season": b["season"],
                             "x": (elo[a["league"]] - elo[b["league"]]) / 100,
                             "y": float(np.mean(logs)),
                             "w": min(a["minutes"], b["minutes"])})
    return pd.DataFrame(rows)


def fit(mv: pd.DataFrame, boot: int = 2000, seed: int = 0) -> dict:
    def slope(d):
        return float((d["w"] * d["x"] * d["y"]).sum() / (d["w"] * d["x"] ** 2).sum())
    use = mv[mv["x"].abs() > 0.05]          # moves between leagues of equal strength say nothing
    beta = slope(use)
    rng = np.random.default_rng(seed)
    draws = [slope(use.iloc[rng.integers(0, len(use), len(use))]) for _ in range(boot)]
    lo, hi = np.percentile(draws, [5, 95])
    return {"beta": round(beta, 3), "ci": [round(float(lo), 3), round(float(hi), 3)],
            "n": int(len(use))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--elo-date", default="2026-05-31")
    a = ap.parse_args()
    elos = {k: v["elo"] for k, v in league_elos(a.elo_date, DATA / "raw").items()}
    df = fotmob.load_fetched(sorted((DATA / "fotmob").glob("*.csv")))
    mv = movers(stints(df), elos)
    result = fit(mv)
    result["method"] = ("weighted least squares through the origin on movers' mean log "
                        "change in attacking per-90s; 90% bootstrap interval")
    result["metrics"] = METRICS
    result["seasons"] = sorted(df["season"].unique())
    (DATA / "beta_fit.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    mv.to_csv(DATA / "movers.csv", index=False)
    print(json.dumps(result))
    print(mv.groupby(["from", "to"]).size().sort_values(ascending=False).head(12).to_string())


if __name__ == "__main__":
    main()
