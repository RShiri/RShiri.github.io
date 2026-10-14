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


def test_fotmob_live_response_regression():
    """A trimmed real matchDetails (Liverpool 4-2 Bournemouth, 15 Aug 2025)."""
    from pathlib import Path
    from pipeline import fetch_fotmob as ff
    path = Path(__file__).parent / "fixtures" / "fotmob_match_4813374_trimmed.json"
    details = json.loads(path.read_text(encoding="utf-8"))
    rows = {r["player"]: r for r in ff.player_rows({"id": 4813374, "date": "2025-08-15"},
                                                   details, "ENG1")}
    # Mamardashvili was an unused sub: no minutes, no row.
    assert set(rows) == {"Virgil van Dijk", "Mohamed Salah", "Cody Gakpo",
                         "Federico Chiesa", "Djordje Petrovic"}
    salah, vvd = rows["Mohamed Salah"], rows["Virgil van Dijk"]
    assert (salah["team"], salah["minutes"], salah["goals"]) == ("Liverpool", 90, 1)
    assert (salah["xg"], salah["xa"], salah["passAcc"], salah["passes"]) == (0.26, 0.11, 18, 30)
    assert salah["npxg"] == salah["xg"]
    assert (vvd["tackles"], vvd["clearances"], vvd["aerials"], vvd["touches"]) == (1, 17, 12, 100)
    # positionId 83/87 are the wide men of the 4-2-3-1, 36 a centre-back, 11 the keeper.
    assert (salah["position"], rows["Cody Gakpo"]["position"], vvd["position"]) == (
        "AMR", "AML", "DC")
    assert rows["Djordje Petrovic"]["position"] == "GK" and rows["Djordje Petrovic"]["saves"] == 6
    # Subs have no slot, only a coarse usual position.
    chiesa = rows["Federico Chiesa"]
    assert chiesa["position"] == "Sub:FW" and chiesa["minutes"] == 8
    # FotMob omits zero stats: no xG key for a keeper who never shot, no xA for Chiesa.
    # In a league that publishes them they are 0, not missing; a cameo has no rating.
    assert rows["Djordje Petrovic"]["xg"] == 0 and chiesa["xa"] == 0
    assert vvd["dribbles"] == 0 and "rating" not in chiesa
    season = fotmob.from_match_rows(pd.DataFrame(list(rows.values())))
    groups = dict(zip(season["name"], season["pos_group"]))
    assert groups == {"Virgil van Dijk": "CB", "Mohamed Salah": "W", "Cody Gakpo": "W",
                      "Federico Chiesa": "FW", "Djordje Petrovic": "GK"}


def test_fotmob_no_xg_league_stays_missing():
    from pipeline import fetch_fotmob as ff
    stat = lambda k, v: {k: {"key": k, "stat": {"value": v}}}
    details = {"general": {}, "content": {"lineup": {}, "playerStats": {
        str(i): {"name": f"P{i}", "stats": [{"stats": {**stat("minutes_played", 90),
                                                       **stat("total_shots", i)}}]}
        for i in (1, 2)}}}
    rows = ff.player_rows({"id": 1, "date": "2025-09-01"}, details, "ISR1")
    assert all("xg" not in r for r in rows) and [r["shots"] for r in rows] == [1, 2]


def test_fotmob_mid_season_move_gets_one_entry_per_league():
    base = {"date": "2026-01-10", "team": "A", "player": "X", "position": "FW", "minutes": 90}
    rows = pd.DataFrame([{**base, "league": "BRA1", "match_id": 1, "player_id": 7},
                         {**base, "league": "ENG1", "match_id": 2, "player_id": 7},
                         {**base, "league": "ENG1", "match_id": 2, "player_id": 8}])
    out = fotmob.from_match_rows(rows)
    assert sorted(out["player_id"]) == ["fotmob:7@BRA1", "fotmob:7@ENG1", "fotmob:8"]


def test_fotmob_pivots_are_central_midfielders():
    from pipeline import fetch_fotmob as ff
    from pipeline.positions import group_from_slot
    group = lambda pid: group_from_slot(ff.slot_from_fotmob({"positionId": pid}))
    # 4-2-3-1 double pivot (64/66), 4-3-1-2 three (63/65/67), 4-1-4-1 anchor (65).
    assert [group(p) for p in (63, 64, 65, 66, 67)] == ["CM"] * 5
