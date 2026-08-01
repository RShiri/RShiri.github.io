"""Network-free unit tests for the f1db-backed season fetcher.

Injects fixtures into the module's caches so the pure assembly logic
(``build_race``, ``assemble_season``, slug/team helpers) is exercised without
touching ``raw.githubusercontent.com``.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fetch_season as fs  # noqa: E402


def setup_function(_):
    fs._yaml_cache.clear()
    fs._driver_cache.clear()
    fs._country_cache.clear()
    fs._driver_cache.update({
        "lando-norris": {"code": "NOR", "name": "Lando Norris", "nat": "GB"},
        "max-verstappen": {"code": "VER", "name": "Max Verstappen", "nat": "NL"},
        "charles-leclerc": {"code": "LEC", "name": "Charles Leclerc", "nat": "MC"},
    })


def test_team_name_mapping_and_fallback():
    assert fs.team_name("red-bull") == "Red Bull Racing"
    assert fs.team_name("kick-sauber") == "Kick Sauber"
    assert fs.team_name("audi") == "Audi"
    assert fs.team_name("some-new-team") == "Some New Team"   # title-case fallback
    assert fs.team_name(None) == ""


def test_country_alpha2_for_flags():
    fs._yaml_cache["countries/netherlands.yml"] = {"alpha2Code": "NL"}
    assert fs.country_alpha2("netherlands") == "NL"
    assert fs.country_alpha2(None) == ""


def test_slug_candidates():
    cands = fs._slug_candidates("Austrian Grand Prix", "Austria", "Spielberg")
    assert cands[0] == "austria"                 # from the name map
    assert "spielberg" in cands                  # locality is a fallback candidate


def test_build_race_upcoming_is_offline():
    ev = {"round": 20, "name": "Qatar Grand Prix", "country": "Qatar",
          "locality": "Lusail", "circuit": "Lusail", "date": "2026-11-29"}
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)   # race is in the future
    race = fs.build_race(2026, ev, now, {"drivers": {}, "teams": {}})
    assert race["status"] == "upcoming" and race["results"] == [] and race["winner"] is None


def test_build_race_completed_parses_f1db_results():
    fs._yaml_cache["seasons/2025/races/01-australia/race-results.yml"] = [
        {"position": 1, "driverId": "lando-norris", "constructorId": "mclaren",
         "points": 25, "gridPosition": 1, "laps": 57, "reasonRetired": None},
        {"position": 2, "driverId": "max-verstappen", "constructorId": "red-bull",
         "points": 18, "gridPosition": 3, "laps": 57, "reasonRetired": None},
        {"position": 3, "driverId": "charles-leclerc", "constructorId": "ferrari",
         "points": 15, "gridPosition": 2, "laps": 57, "reasonRetired": None},
    ]
    fs._yaml_cache["seasons/2025/races/01-australia/fast-laps.yml"] = None
    # extra per-race files that feed the stats (kept offline via the cache)
    fs._yaml_cache["seasons/2025/races/01-australia/pit-stops.yml"] = [
        {"driverId": "max-verstappen", "stop": 1, "lap": 20, "time": "12.5"},  # fastest
        {"driverId": "lando-norris", "stop": 1, "lap": 18, "time": "13.0"},
        {"driverId": "lando-norris", "stop": 2, "lap": 40, "time": "13.5"},
    ]
    fs._yaml_cache["seasons/2025/races/01-australia/qualifying-results.yml"] = [
        {"driverId": "lando-norris", "position": 1},
        {"driverId": "charles-leclerc", "position": 2},
        {"driverId": "max-verstappen", "position": 3},
    ]
    fs._yaml_cache["seasons/2025/races/01-australia/driver-of-the-day-results.yml"] = [
        {"driverId": "max-verstappen", "position": 1, "percentage": 30.0},
    ]
    ev = {"round": 1, "name": "Australian Grand Prix", "country": "Australia",
          "locality": "Melbourne", "circuit": "Melbourne", "date": "2025-03-16"}
    wins = {"drivers": {}, "teams": {}}
    race = fs.build_race(2025, ev, datetime(2025, 7, 1, tzinfo=timezone.utc), wins)

    assert race["status"] == "completed"
    assert race["winner"] == {"code": "NOR", "name": "Lando Norris", "nat": "GB", "team": "McLaren"}
    assert [p["code"] for p in race["podium"]] == ["NOR", "VER", "LEC"]
    assert race["results"][1]["team"] == "Red Bull Racing"
    assert wins["drivers"]["NOR"] == 1 and wins["teams"]["McLaren"] == 1

    # enrichment: Driver of the Day, poles (qualifying P1), and stationary
    # estimates = stop time minus the race's fastest stop (12.5) + base (2.0).
    assert race["dotd"] == "VER"
    nor_row, ver_row = race["results"][0], race["results"][1]
    assert nor_row["qpos"] == 1 and nor_row["stops"] == 2 and nor_row["pit_est"] == [2.5, 3.0]
    assert ver_row["qpos"] == 3 and ver_row["stops"] == 1 and ver_row["pit_est"] == [2.0]


def test_reconcile_postponed_flags_skipped_round():
    # Round 7 sits between two COMPLETED rounds but has no f1db result, and a
    # later round (8) is already done -> it was skipped, so mark it postponed.
    # Round 10 is a genuine future race and must stay upcoming.
    races = [
        {"round": 6, "status": "completed"},
        {"round": 7, "status": "upcoming"},   # Barcelona: past date, never held
        {"round": 8, "status": "completed"},
        {"round": 9, "status": "completed"},
        {"round": 10, "status": "upcoming"},  # genuinely in the future
    ]
    fs.reconcile_postponed(races)
    by = {r["round"]: r["status"] for r in races}
    assert by == {6: "completed", 7: "postponed", 8: "completed",
                  9: "completed", 10: "upcoming"}


def test_reconcile_postponed_keeps_just_finished_race_upcoming():
    # The latest race has happened but f1db hasn't published it yet: no LATER
    # round is complete, so it must remain upcoming (not be flagged postponed).
    races = [
        {"round": 8, "status": "completed"},
        {"round": 9, "status": "upcoming"},   # just raced, results pending
    ]
    fs.reconcile_postponed(races)
    assert [r["status"] for r in races] == ["completed", "upcoming"]


def test_topup_standings_folds_manual_points_and_reranks():
    fs._driver_cache.update({
        "kimi-antonelli": {"code": "ANT", "name": "Kimi Antonelli", "nat": "IT"},
    })
    # f1db order (Barcelona omitted): RUS ahead of HAM, LEC ahead of NOR.
    ds = [
        {"position": 1, "driverId": "kimi-antonelli", "points": 179},
        {"position": 2, "driverId": "george-russell", "points": 154},
        {"position": 3, "driverId": "lewis-hamilton", "points": 147},
        {"position": 4, "driverId": "charles-leclerc", "points": 108},
        {"position": 5, "driverId": "lando-norris", "points": 97},
    ]
    fs._driver_cache.update({
        "george-russell": {"code": "RUS", "name": "George Russell", "nat": "GB"},
        "lewis-hamilton": {"code": "HAM", "name": "Lewis Hamilton", "nat": "GB"},
        "charles-leclerc": {"code": "LEC", "name": "Charles Leclerc", "nat": "MC"},
        "lando-norris": {"code": "NOR", "name": "Lando Norris", "nat": "GB"},
    })
    cs = [{"position": 1, "constructorId": "mercedes", "points": 333},
          {"position": 2, "constructorId": "ferrari", "points": 255}]
    manual = [{"results": [
        {"code": "HAM", "team": "Ferrari", "points": 25},
        {"code": "RUS", "team": "Mercedes", "points": 18},
        {"code": "NOR", "team": "McLaren", "points": 15},
        {"code": "ANT", "team": "Mercedes", "points": 0},   # DNF, no points
    ]}]
    ds2, cs2 = fs.topup_standings(ds, cs, manual)

    got = [(s["position"], fs.resolve_driver(s["driverId"])["code"], s["points"]) for s in ds2]
    # RUS 172 and HAM 172 tie -> RUS stays ahead (stable sort keeps f1db countback
    # order); NOR 112 leapfrogs LEC 108.
    assert got == [(1, "ANT", 179), (2, "RUS", 172), (3, "HAM", 172),
                   (4, "NOR", 112), (5, "LEC", 108)]
    assert cs2[0] == {"position": 1, "constructorId": "mercedes", "points": 351}


def test_topup_standings_noop_without_manual_races():
    ds = [{"position": 1, "driverId": "lando-norris", "points": 100}]
    cs = [{"position": 1, "constructorId": "mclaren", "points": 200}]
    ds2, cs2 = fs.topup_standings(ds, cs, [])
    assert ds2 is ds and cs2 is cs   # untouched when nothing was applied


def test_assemble_season_schema():
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    driver_standings = [
        {"position": 1, "driverId": "lando-norris", "points": 423},
        {"position": 2, "driverId": "max-verstappen", "points": 421},
    ]
    constructor_standings = [
        {"position": 1, "constructorId": "mclaren", "points": 833},
        {"position": 2, "constructorId": "red-bull", "points": 451},
    ]
    team_by_code = {"NOR": "McLaren", "VER": "Red Bull Racing"}
    wins = {"drivers": {"NOR": 7, "VER": 8}, "teams": {"McLaren": 14}}
    d = fs.assemble_season(2025, [], driver_standings, constructor_standings,
                           team_by_code, wins, now)
    assert set(d) == {"season", "updated", "source", "races", "drivers",
                      "constructors", "stats"}
    assert d["drivers"][0] == {"pos": 1, "code": "NOR", "name": "Lando Norris",
                               "nat": "GB", "team": "McLaren", "points": 423, "wins": 7}
    assert d["constructors"][0] == {"pos": 1, "team": "McLaren", "points": 833, "wins": 14}
    assert d["stats"] == []          # no races supplied -> no per-driver rows


def test_build_driver_stats_aggregates_across_races():
    def row(code, name, pos, grid, pts, status="Finished", qpos=None,
            stops=None, pit_est=None, laps=57):
        return {"code": code, "name": name, "nat": "", "pos": pos, "grid": grid,
                "points": pts, "status": status, "qpos": qpos, "stops": stops,
                "pit_est": pit_est, "laps": laps}

    races = [
        {"status": "completed", "dotd": "VER", "results": [
            row("NOR", "Lando Norris", 1, 1, 25, qpos=1, stops=2, pit_est=[2.4, 2.6]),
            row("VER", "Max Verstappen", 2, 4, 18, qpos=3, stops=2, pit_est=[2.8, 3.0]),
        ]},
        {"status": "completed", "dotd": None, "results": [
            row("NOR", "Lando Norris", 3, 5, 15, qpos=2, stops=1, pit_est=[2.2]),
            row("VER", "Max Verstappen", None, 2, 0, status="Accident", qpos=1,
                stops=1, pit_est=[3.4], laps=10),
        ]},
        {"status": "upcoming", "results": []},   # ignored
    ]
    stats = fs.build_driver_stats(races, {"NOR": "McLaren", "VER": "Red Bull Racing"})
    by = {s["code"]: s for s in stats}

    nor = by["NOR"]
    assert nor["starts"] == 2 and nor["wins"] == 1 and nor["podiums"] == 2
    assert nor["poles"] == 1 and nor["dnf"] == 0 and nor["points"] == 40
    assert nor["avg_finish"] == 2.0 and nor["avg_grid"] == 3.0
    assert nor["gained"] == 2                       # (1-1) + (5-3)
    assert nor["avg_stops"] == 1.5                  # (2 + 1) / 2
    assert nor["stop_s"] == 2.4                      # median of [2.4, 2.6, 2.2]
    assert nor["team"] == "McLaren" and nor["laps_led"] is None

    ver = by["VER"]
    assert ver["poles"] == 1 and ver["dnf"] == 1 and ver["dotd"] == 1
    assert ver["gained"] == 2                        # only the finished race counts (4-2)
    assert stats[0]["code"] == "NOR"                 # sorted by points desc


def test_build_driver_stats_uses_official_points_when_given():
    races = [{"status": "completed", "dotd": None, "results": [
        {"code": "VER", "name": "Max Verstappen", "nat": "", "pos": 2, "grid": 2,
         "points": 18, "status": "Finished", "laps": 57},   # sprint points not in GP result
    ]}]
    # Championship total (incl. sprint) differs from the summed GP points.
    stats = fs.build_driver_stats(races, {"VER": "Red Bull Racing"}, {"VER": 26})
    assert stats[0]["points"] == 26


def test_build_driver_stats_surfaces_laps_led_when_present():
    races = [{"status": "completed", "dotd": None, "results": [
        {"code": "VER", "name": "Max Verstappen", "nat": "", "pos": 1, "grid": 1,
         "points": 25, "status": "Finished", "laps": 57, "led": 40},
    ]}]
    stats = fs.build_driver_stats(races, {"VER": "Red Bull Racing"})
    assert stats[0]["laps_led"] == 40
