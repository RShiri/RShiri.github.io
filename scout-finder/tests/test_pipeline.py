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
