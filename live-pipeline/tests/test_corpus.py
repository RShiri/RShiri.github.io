"""Tests for the multi-corpus loader (tradepipe/corpus.py).

The loader is tested against tiny synthetic matches_detail files written
into a tmp dir, so the suite never depends on the scraper clones being
present. Run from the repo root:
    python3 -m pytest live-pipeline/tests/test_corpus.py -q
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "winprob_corpus", HERE.parent / "tradepipe" / "corpus.py")
corpus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(corpus)


def write_match(dir_path, name, home, away, date, stage, shots, goals=()):
    obj = {
        "home": {"name": home, "raw": home, "score": 0, "pens": None, "color": "#111"},
        "away": {"name": away, "raw": away, "score": 0, "pens": None, "color": "#222"},
        "date": date, "venue": "", "stage": stage, "maxMin": 95,
        "shots": list(shots), "goals": list(goals), "id": name,
    }
    path = Path(dir_path) / (name + ".js")
    path.write_text("window.MATCH_DETAIL = %s;\n" % json.dumps(obj),
                    encoding="utf-8")
    return path


def shot(team, minute, xg, goal=False):
    return {"team": team, "min": minute, "sec": 0, "xg": xg, "goal": goal,
            "onTarget": goal, "blocked": False, "post": False, "big": False,
            "body": "Right Foot", "sit": "Open Play", "x": 90.0, "y": 50.0,
            "gy": 50.0, "gz": 10.0, "player": "P"}


def test_league_season_derivation():
    assert corpus.league_season("2022-08-05") == "2022-23"
    assert corpus.league_season("2023-05-28") == "2022-23"
    assert corpus.league_season("2025-12-26") == "2025-26"
    assert corpus.league_season("2026-01-04") == "2025-26"


def test_league_match_normalization(tmp_path):
    # a 90+3' stoppage shot: leagues have no extra time, so it counts (at 90')
    write_match(tmp_path, "m1", "Arsenal", "Chelsea", "2024-02-10",
                "Premier League",
                shots=[shot("home", 12, 0.3), shot("home", 93, 0.5, goal=True),
                       shot("away", 40, 0.2)])
    matches = list(corpus.iter_matches([("EPL", tmp_path, None)]))
    assert len(matches) == 1
    M = matches[0]
    assert M["competition"] == "EPL"
    assert M["season"] == "2023-24"
    assert M["home"] == "Arsenal" and M["away"] == "Chelsea"
    assert M["has_extra_time"] is False
    assert M["is_neutral"] is False
    assert abs(M["xg"][0] - 0.8) < 1e-9      # stoppage shot included
    assert abs(M["xg"][1] - 0.2) < 1e-9


def test_wc_group_vs_knockout_and_stage_labels(tmp_path):
    # group-ish labels in all their scraped disguises => no extra time
    write_match(tmp_path, "g1", "France", "Peru", "2018-06-21",
                "World Cup Grp. C", shots=[shot("home", 92, 0.4)])
    # knockout label => extra time, min > 90 xG excluded from the 90' total
    write_match(tmp_path, "k1", "France", "Croatia", "2018-07-15",
                "Final", shots=[shot("home", 30, 0.6), shot("home", 100, 0.9)])
    matches = {M["home"] + "/" + M["away"]: M
               for M in corpus.iter_matches([("WC", tmp_path, 2018)])}
    g, k = matches["France/Peru"], matches["France/Croatia"]
    assert g["has_extra_time"] is False and g["is_neutral"] is True
    assert abs(g["xg"][0] - 0.4) < 1e-9      # 92' folds to 90, still counts
    assert k["has_extra_time"] is True
    assert abs(k["xg"][0] - 0.6) < 1e-9      # the 100' ET shot is excluded
    assert g["season"] == k["season"] == "2018"


def test_wc_empty_stage_date_window(tmp_path):
    # empty stage: group unless the date is in the WC2026 knockout window
    write_match(tmp_path, "e1", "Iran", "New Zealand", "", "", shots=[])
    write_match(tmp_path, "e2", "Spain", "Belgium", "2026-07-10", "", shots=[])
    matches = {M["home"]: M for M in corpus.iter_matches([("WC", tmp_path, 2026)])}
    assert matches["Iran"]["has_extra_time"] is False      # no date -> group
    assert matches["Spain"]["has_extra_time"] is True      # knockout window


def test_wc2026_dedup_prefers_real_id(tmp_path):
    same = dict(home="South Africa", away="Canada", date="2026-06-29",
                stage="Group Stage", shots=[shot("away", 55, 0.7, goal=True)])
    write_match(tmp_path, "2026_06_28_2A_vs_2B", **same)              # placeholder id
    write_match(tmp_path, "2026_06_29_South_Africa_vs_Canada", **same)  # real id
    write_match(tmp_path, "2026_06_30_Mexico_vs_Japan", "Mexico", "Japan",
                "2026-06-30", "Group Stage", shots=[])
    # _index.js must be skipped, never parsed
    (tmp_path / "_index.js").write_text("window.MATCH_INDEX = [];\n")
    matches = list(corpus.iter_matches([("WC", tmp_path, 2026)]))
    assert len(matches) == 2                 # dup pair collapsed to one
    assert {(M["home"], M["away"]) for M in matches} == {
        ("South Africa", "Canada"), ("Mexico", "Japan")}
