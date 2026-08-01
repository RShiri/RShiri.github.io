"""Network-free unit tests for the scraper's pure transforms.

These build tiny DataFrames shaped exactly like fastf1's real output (verified
against fastf1 3.8) and assert the transformation logic — no F1 API needed, so
they run anywhere (including CI) in milliseconds. This is what makes the data
layer modular: the transforms are decoupled from the download.

Run with:  pytest -q
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scraper  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures — minimal fastf1-shaped frames
# --------------------------------------------------------------------------- #
def _laps():
    """Two drivers, 4 laps. VER pits on lap 3; TrackStatus shows VSC on lap 2."""
    rows = []
    plan = {
        "VER": [(1, 1, "SOFT", False, "1"), (2, 1, "SOFT", False, "6"),
                (3, 2, "SOFT", True, "1"), (4, 1, "HARD", False, "1")],
        "HAM": [(1, 2, "MEDIUM", False, "1"), (2, 2, "MEDIUM", False, "6"),
                (3, 1, "MEDIUM", False, "1"), (4, 2, "MEDIUM", False, "1")],
    }
    for drv, laps in plan.items():
        for lap, pos, comp, pit, ts in laps:
            rows.append({
                "Driver": drv, "DriverNumber": "1" if drv == "VER" else "44",
                "Team": "Red Bull Racing" if drv == "VER" else "Mercedes",
                "LapNumber": float(lap), "Position": float(pos), "Compound": comp,
                "PitInTime": pd.Timedelta(seconds=90) if pit else pd.NaT,
                "TrackStatus": ts,
            })
    return pd.DataFrame(rows)


def _race_control_messages():
    t0 = pd.Timestamp("2024-01-01 12:00:00")
    return pd.DataFrame([
        {"Time": t0, "Message": "VIRTUAL SAFETY CAR DEPLOYED",
         "Status": "DEPLOYED", "Lap": 2},
        {"Time": t0 + pd.Timedelta(minutes=2), "Message": "VIRTUAL SAFETY CAR ENDING",
         "Status": "ENDING", "Lap": 2},
    ])


def _results():
    return pd.DataFrame([
        {"Abbreviation": "VER", "DriverNumber": "1", "FullName": "Max Verstappen",
         "TeamName": "Red Bull Racing", "TeamColor": "3671C6",
         "Position": 1.0, "Status": "Finished"},
        {"Abbreviation": "HAM", "DriverNumber": "44", "FullName": "Lewis Hamilton",
         "TeamName": "Mercedes", "TeamColor": "27F4D2",
         "Position": 20.0, "Status": "Retired"},
    ])


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_vsc_from_messages():
    assert scraper.extract_vsc_laps_from_messages(_race_control_messages()) == {2}


def test_vsc_messages_take_precedence_but_fallback_works():
    # With messages present -> use them.
    assert scraper.extract_vsc_laps(_race_control_messages(), _laps()) == {2}
    # With no messages -> fall back to TrackStatus code '6'/'7'.
    empty = pd.DataFrame(columns=["Time", "Message", "Status", "Lap"])
    assert scraper.extract_vsc_laps(empty, _laps()) == {2}


def test_pit_stop_tagging():
    df = scraper.build_laps_dataframe(_laps(), {2})
    ver_pits = set(int(x) for x in df[(df.Driver == "VER") & df.is_pit_stop]["LapNumber"])
    assert ver_pits == {3}                       # VER's only pit-in lap
    assert df["is_pit_stop"].sum() == 1          # nobody else pits


def test_tidy_schema_and_vsc_flag():
    df = scraper.build_laps_dataframe(_laps(), {2})
    assert set(df.columns) == {
        "Driver", "DriverNumber", "Team", "LapNumber",
        "Position", "Compound", "is_pit_stop", "is_vsc",
    }
    assert df.loc[df.LapNumber == 2, "is_vsc"].all()
    assert not df.loc[df.LapNumber == 1, "is_vsc"].any()
    # Positions become a nullable integer type (grid slots are whole numbers).
    assert str(df["Position"].dtype) == "Int64"


def test_driver_meta_colors():
    meta = scraper.build_driver_meta(_results(), _laps())
    assert meta["VER"]["color"] == "#3671C6"     # '#' prefix added
    assert meta["HAM"]["full_name"] == "Lewis Hamilton"
    assert set(meta) == {"VER", "HAM"}


def test_driver_meta_finished_vs_retired():
    meta = scraper.build_driver_meta(_results(), _laps())
    assert meta["VER"]["finished"] is True and meta["VER"]["classified"] == 1
    assert meta["HAM"]["finished"] is False and meta["HAM"]["classified"] == 20


def test_is_finished_status_parsing():
    assert scraper._is_finished("Finished")
    assert scraper._is_finished("+1 Lap")        # lapped cars are classified
    assert not scraper._is_finished("Retired")
    assert not scraper._is_finished("Accident")
    assert scraper._is_finished("")              # unknown -> safe default


def test_driver_meta_fallback_color_when_results_missing():
    meta = scraper.build_driver_meta(None, _laps())
    # Every driver in the laps still gets a stable, non-empty colour.
    assert meta["VER"]["color"] and meta["HAM"]["color"]
    assert meta["VER"]["color"] != meta["HAM"]["color"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
