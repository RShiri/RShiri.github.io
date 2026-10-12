import json

import pandas as pd

from pipeline import build
from pipeline.sources import fotmob, understat


def test_understat_blob_and_rows():
    players = [{"id": "8260", "player_name": "Ødegaard", "games": "30", "time": "2500",
                "goals": "5", "assists": "8", "xG": "4.1", "npxG": "3.3", "xA": "7.2",
                "shots": "50", "key_passes": "80", "xGChain": "15.0", "xGBuildup": "6.0",
                "position": "M S", "team_title": "Arsenal"}]
    escaped = "".join(f"\\x{b:02X}" for b in json.dumps(players).encode("utf-8"))
    page = f"<script>var playersData = JSON.parse('{escaped}');</script>"
    parsed = understat.players_from_page(page)
    assert parsed[0]["player_name"] == "Ødegaard"
    row = understat.to_rows(parsed, "EPL", "2025-26").iloc[0]
    assert row["player_id"] == "understat:8260" and row["pos_group"] == "CM"
    assert row["xg_chain"] == 15.0


def test_fotmob_season_rollup():
    rows = pd.DataFrame([
        {"match_id": 1, "date": "2026-08-20", "team": "A", "opponent": "B", "player_id": 7,
         "player": "X", "position": "DC", "minutes": 90, "xg": 0.1, "passes": 50, "passAcc": 45},
        {"match_id": 2, "date": "2026-08-27", "team": "A", "opponent": "C", "player_id": 7,
         "player": "X", "position": "Sub", "minutes": 20, "xg": 0.0, "passes": 10, "passAcc": 9},
    ])
    for c in fotmob.SUM_COLS:
        if c not in rows:
            rows[c] = 0
    out = fotmob.from_match_rows(rows).iloc[0]
    assert out["season"] == "2026-27" and out["pos_group"] == "CB"
    assert out["minutes"] == 110 and out["passes_accurate"] == 54


def test_percentiles_and_similarity():
    n = 10
    df = pd.DataFrame({
        "source": "fotmob", "league": "EPL", "season": "2025-26",
        "player_id": [f"p{i}" for i in range(n)], "name": [f"P{i}" for i in range(n)],
        "team": "T", "pos_group": "FW", "matches": 30, "minutes": 2700,
        "xg": range(n), "shots": [3 * i + 1 for i in range(n)], "xa": [n - i for i in range(n)],
    })
    data = build.build(df)
    by_id = {p["id"]: p for p in data["players"]}
    assert by_id["p9"]["pct"]["xg"] == 100 and by_id["p0"]["pct"]["xg"] == 10
    assert by_id["p9"]["similar"][0]["id"] == "p8"
    assert "xg" in by_id["p9"]["strengths"]


def test_universe_missing_stat_and_league_factor():
    rows = []
    for lg, has_xg in (("ENG1", True), ("ISR1", False)):
        for i in range(8):
            rows.append({"source": "fotmob", "season": "2025-26", "league": lg,
                         "player_id": f"{lg}{i}", "name": f"{lg}{i}", "team": "T",
                         "pos_group": "FW", "matches": 30, "minutes": 2700,
                         "xg": float(i) if has_xg else float("nan"),
                         "shots": 10.0 + i, "xa": 1.0})
    data = build.build(pd.DataFrame(rows), {"ENG1": 1.0, "ISR1": 0.7})
    by_id = {p["id"]: p for p in data["players"]}
    assert by_id["ISR17"]["per90"]["xg"] is None and by_id["ISR17"]["pct"]["xg"] is None
    # Same raw shots, but Israel's are scaled down, so the English player ranks higher overall.
    assert by_id["ENG17"]["pct"]["shots"] > by_id["ISR17"]["pct"]["shots"]
    assert by_id["ENG17"]["pct_league"]["shots"] == by_id["ISR17"]["pct_league"]["shots"] == 100


def test_fotmob_player_rows_parse():
    from pipeline import fetch_fotmob as ff
    details = {
        "general": {"homeTeam": {"id": 1, "name": "Home"}, "awayTeam": {"id": 2, "name": "Away"}},
        "content": {
            "lineup": {"homeTeam": {"starters": [{"id": 10, "positionId": 34}], "subs": []}},
            "playerStats": {"10": {"name": "A", "teamId": 1, "stats": [{"stats": {
                "Minutes": {"key": "minutes_played", "stat": {"value": 90}},
                "xG": {"key": "expected_goals", "stat": {"value": 0.31}},
                "Passes": {"key": "accurate_passes", "stat": {"value": 40, "total": 45}},
                "Duels": {"key": "aerials_won", "stat": {"value": "3/5 (60%)"}},
            }}]}},
        },
    }
    r = ff.player_rows({"id": 99, "date": "2025-09-01"}, details, "ENG1")[0]
    assert (r["team"], r["position"], r["minutes"], r["xg"]) == ("Home", "DC", 90, 0.31)
    assert (r["passAcc"], r["passes"], r["aerials"]) == (40, 45, 3)
