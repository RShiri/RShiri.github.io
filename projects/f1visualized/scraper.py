"""Stage 1 — Dynamic data extraction & transformation.

Fetches the **most recently completed** Formula 1 Grand Prix (race session)
with :mod:`fastf1`, then transforms the raw timing data into a tidy, analysis
ready ``pandas`` table plus a small metadata sidecar.

Design notes
------------
* **No hard-coded round.** ``find_latest_completed_session`` walks the event
  schedule backwards from *now* and loads the first race that actually has
  timing data available. That gracefully handles the window right after a race
  (data not published yet) by falling back to the previous round.
* **Modular / future-proof.** Every public function accepts an explicit
  ``year`` / ``round_number`` so the exact same code can back-fill historical
  races or feed a live dashboard later — nothing about "latest" is baked into
  the transforms. The heavy lifting lives in *pure* functions that take plain
  DataFrames, so they are trivially unit-testable without the network.

Run standalone::

    python scraper.py                 # latest completed race
    python scraper.py --year 2024 --round 11   # a specific historical race
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

import pandas as pd

import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s"
)
log = logging.getLogger("scraper")

# Imported lazily inside functions so that ``import scraper`` stays cheap and so
# unit tests can exercise the pure transforms without fastf1 installed.
_fastf1 = None


def _fastf1_module():
    """Import fastf1 once, enabling its on-disk cache."""
    global _fastf1
    if _fastf1 is None:
        import fastf1  # noqa: WPS433 (deliberate lazy import)

        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(config.CACHE_DIR))
        _fastf1 = fastf1
    return _fastf1


# --------------------------------------------------------------------------- #
# Locating the target session
# --------------------------------------------------------------------------- #
def _utcnow() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None)


def iter_completed_rounds(
    reference_date: Optional[pd.Timestamp] = None,
    earliest_season: int = config.EARLIEST_SUPPORTED_SEASON,
) -> Iterator[tuple[int, int]]:
    """Yield ``(year, round_number)`` for completed races, most-recent first.

    A race counts as "completed" once its race-session start time is in the
    past relative to ``reference_date``. Seasons are scanned newest-first and,
    within a season, rounds are scanned highest-first.
    """
    fastf1 = _fastf1_module()
    now = reference_date if reference_date is not None else _utcnow()

    for year in range(now.year, earliest_season - 1, -1):
        try:
            schedule = fastf1.get_event_schedule(year, include_testing=False)
        except Exception as exc:  # pragma: no cover - network dependent
            log.warning("Could not load %s schedule: %s", year, exc)
            continue

        # ``Session5DateUtc`` is the race session for every weekend format
        # (conventional and sprint alike). Fall back to the event date.
        race_dates = schedule.get("Session5DateUtc")
        if race_dates is None:
            race_dates = schedule.get("EventDate")

        completed = schedule.loc[pd.to_datetime(race_dates) <= now]
        completed = completed.sort_values("RoundNumber", ascending=False)
        for _, event in completed.iterrows():
            yield year, int(event["RoundNumber"])


def load_race_session(year: int, round_number: int):
    """Load a single race session, or return ``None`` if its data is missing.

    ``telemetry`` and ``weather`` are skipped for speed; we only need laps and
    race-control messages.
    """
    fastf1 = _fastf1_module()
    try:
        session = fastf1.get_session(year, round_number, "R")
        session.load(laps=True, telemetry=False, weather=False, messages=True)
    except Exception as exc:  # data not yet published, network hiccup, ...
        log.warning("Could not load %s round %s: %s", year, round_number, exc)
        return None

    if session.laps is None or len(session.laps) == 0:
        log.warning("Session %s round %s loaded but has no laps.", year, round_number)
        return None
    return session


def find_latest_completed_session(
    year: Optional[int] = None,
    round_number: Optional[int] = None,
    reference_date: Optional[pd.Timestamp] = None,
    max_attempts: int = 8,
):
    """Return a loaded race session.

    * If ``year`` **and** ``round_number`` are given, load exactly that race.
    * Otherwise walk the schedule backwards and return the first race whose
      timing data is actually available (up to ``max_attempts`` candidates).
    """
    if year is not None and round_number is not None:
        session = load_race_session(year, round_number)
        if session is None:
            raise RuntimeError(f"No data available for {year} round {round_number}.")
        return session

    attempts = 0
    for cand_year, cand_round in iter_completed_rounds(reference_date):
        attempts += 1
        log.info("Trying candidate: %s round %s", cand_year, cand_round)
        session = load_race_session(cand_year, cand_round)
        if session is not None:
            return session
        if attempts >= max_attempts:
            break
    raise RuntimeError(
        "Could not find any completed race with available data "
        f"after {attempts} attempt(s)."
    )


# --------------------------------------------------------------------------- #
# Pure transforms  (operate on plain DataFrames — unit-testable, no network)
# --------------------------------------------------------------------------- #
def extract_vsc_laps_from_messages(race_control_messages: pd.DataFrame) -> set[int]:
    """Identify laps on which a Virtual Safety Car was active.

    Uses the race-control message feed: each VSC ``DEPLOYED`` message opens a
    window and the matching ``ENDING`` message closes it. Every lap in between
    (inclusive) is flagged. The ``Lap`` column on each message gives us the
    exact lap without any time-base reconciliation.
    """
    if race_control_messages is None or len(race_control_messages) == 0:
        return set()
    if "Message" not in race_control_messages.columns:
        return set()

    msgs = race_control_messages.copy()
    msgs["_msg"] = msgs["Message"].astype(str).str.upper()
    vsc = msgs[msgs["_msg"].str.contains("VIRTUAL SAFETY CAR")]
    if vsc.empty:
        return set()
    if "Time" in vsc.columns:
        vsc = vsc.sort_values("Time")

    laps: set[int] = set()
    open_lap: Optional[int] = None
    for _, row in vsc.iterrows():
        lap = row.get("Lap")
        lap = int(lap) if pd.notna(lap) else None
        status = str(row.get("Status", "")).upper()
        message = row["_msg"]

        if "DEPLOYED" in message or status == "DEPLOYED":
            open_lap = lap
        elif "ENDING" in message or status == "ENDING":
            if open_lap is not None and lap is not None:
                laps.update(range(open_lap, lap + 1))
            elif lap is not None:
                laps.add(lap)
            open_lap = None

    if open_lap is not None:  # deployment never explicitly closed
        laps.add(open_lap)
    return laps


def extract_vsc_laps_from_track_status(laps: pd.DataFrame) -> set[int]:
    """Fallback VSC detection from per-lap ``TrackStatus`` codes.

    Track-status code ``6`` = "VSC deployed", ``7`` = "VSC ending". A lap whose
    status string contains either code saw VSC running for part of the lap.
    """
    if laps is None or "TrackStatus" not in laps.columns:
        return set()
    status = laps["TrackStatus"].astype(str)
    is_vsc = status.str.contains("6") | status.str.contains("7")
    vsc_laps = laps.loc[is_vsc, "LapNumber"].dropna()
    return {int(x) for x in vsc_laps.unique()}


def extract_vsc_laps(
    race_control_messages: pd.DataFrame, laps: pd.DataFrame
) -> set[int]:
    """VSC laps from race-control messages, with TrackStatus as a safety net."""
    vsc = extract_vsc_laps_from_messages(race_control_messages)
    if not vsc:
        vsc = extract_vsc_laps_from_track_status(laps)
        if vsc:
            log.info("VSC laps derived from TrackStatus fallback.")
    return vsc


def build_laps_dataframe(laps: pd.DataFrame, vsc_laps: set[int]) -> pd.DataFrame:
    """Transform raw fastf1 laps into a clean, tidy lap-by-lap table.

    One row per driver per lap with the columns the animator needs:
    ``Driver, DriverNumber, Team, LapNumber, Position, Compound,
    is_pit_stop, is_vsc``.
    """
    wanted = [
        "Driver", "DriverNumber", "Team",
        "LapNumber", "Position", "Compound", "PitInTime", "TrackStatus",
    ]
    present = [c for c in wanted if c in laps.columns]
    df = laps.loc[:, present].copy()

    # A driver "entered the pit lane" on a lap iff PitInTime is recorded.
    df["is_pit_stop"] = (
        df["PitInTime"].notna() if "PitInTime" in df.columns else False
    )

    df["LapNumber"] = pd.to_numeric(df["LapNumber"], errors="coerce").astype("Int64")
    if "Position" in df.columns:
        df["Position"] = (
            pd.to_numeric(df["Position"], errors="coerce").round().astype("Int64")
        )
    if "Compound" in df.columns:
        df["Compound"] = (
            df["Compound"].astype(str).str.upper().replace({"NAN": "UNKNOWN", "": "UNKNOWN"})
        )
    else:
        df["Compound"] = "UNKNOWN"

    df = df.dropna(subset=["LapNumber"])
    df["is_vsc"] = df["LapNumber"].astype(int).isin(vsc_laps)

    df = df.drop(columns=[c for c in ("PitInTime", "TrackStatus") if c in df.columns])
    ordered = [
        "Driver", "DriverNumber", "Team", "LapNumber",
        "Position", "Compound", "is_pit_stop", "is_vsc",
    ]
    df = df.loc[:, [c for c in ordered if c in df.columns]]
    return df.sort_values(["LapNumber", "Position"]).reset_index(drop=True)


def _normalise_color(value) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    return value if value.startswith("#") else f"#{value}"


def _is_finished(status: str) -> bool:
    """Classify a results ``Status`` string as finished vs. retired.

    ``Finished`` and lapped classifications (``+1 Lap``, ``+2 Laps``) count as
    finished; anything else (``Retired``, ``Accident``, ``Engine``, ...) is a
    DNF. Unknown/empty status defaults to finished (safe fallback).
    """
    s = (status or "").strip().lower()
    if s == "":
        return True
    return ("finished" in s) or ("lap" in s)


def build_driver_meta(results: Optional[pd.DataFrame], laps: pd.DataFrame) -> dict:
    """Map each driver abbreviation to name, team, number, colour and result.

    Prefers fastf1's official ``results`` (which carries the real ``TeamColor``
    plus final classification and finish status) and guarantees an entry — with
    a stable fallback colour — for every driver that appears in the lap data.
    The ``classified`` position (DNFs already ranked at the bottom) and
    ``finished`` flag let the animator drop retired drivers to last.
    """
    meta: dict[str, dict] = {}

    if results is not None and len(results):
        for _, row in results.iterrows():
            abbr = row.get("Abbreviation")
            if not isinstance(abbr, str) or not abbr:
                continue
            status = str(row.get("Status") or "")
            classified = row.get("Position")
            classified = int(classified) if pd.notna(classified) else None
            meta[abbr] = {
                "full_name": str(row.get("FullName") or abbr),
                "team": str(row.get("TeamName") or ""),
                "number": str(row.get("DriverNumber") or "").split(".")[0],
                "color": _normalise_color(row.get("TeamColor")),
                "status": status,
                "finished": _is_finished(status),
                "classified": classified,
            }

    drivers_in_laps = (
        laps["Driver"].dropna().unique().tolist() if "Driver" in laps.columns else []
    )
    for abbr in drivers_in_laps:
        meta.setdefault(
            abbr,
            {"full_name": abbr, "team": "", "number": "", "color": None,
             "status": "", "finished": True, "classified": None},
        )

    # Deal out fallback colours to anyone still missing one, avoiding clashes.
    used = {m["color"] for m in meta.values() if m["color"]}
    palette = [c for c in config.FALLBACK_TEAM_COLORS if c not in used]
    fallback = iter(palette + config.FALLBACK_TEAM_COLORS)
    for abbr in sorted(meta):
        if not meta[abbr]["color"]:
            meta[abbr]["color"] = next(fallback)
    return meta


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def _safe_results(session):
    try:
        results = session.results
        if results is not None and len(results):
            return results
    except Exception:  # driver info unavailable for a very fresh session
        pass
    return None


def process_session(session, year: int) -> tuple[pd.DataFrame, dict]:
    """Turn a loaded fastf1 session into ``(tidy_laps_df, metadata_dict)``."""
    laps = pd.DataFrame(session.laps)
    results = _safe_results(session)
    try:
        rcm = session.race_control_messages
    except Exception:
        rcm = None

    vsc_laps = extract_vsc_laps(rcm, laps)
    df = build_laps_dataframe(laps, vsc_laps)
    drivers = build_driver_meta(results, laps)

    total_laps = None
    try:
        if session.total_laps:
            total_laps = int(session.total_laps)
    except Exception:
        total_laps = None
    if not total_laps and len(df):
        total_laps = int(df["LapNumber"].max())

    event = session.event
    meta = {
        "year": int(year),
        "round": int(event.get("RoundNumber", 0)),
        "event_name": str(event.get("EventName", "Grand Prix")),
        "official_name": str(event.get("OfficialEventName", "")),
        "location": str(event.get("Location", "")),
        "country": str(event.get("Country", "")),
        "session": "Race",
        "total_laps": int(total_laps or 0),
        "generated_utc": _utcnow().isoformat(),
        "vsc_laps": sorted(vsc_laps),
        "drivers": drivers,
    }
    log.info(
        "Processed %s %s (round %s): %d drivers, %d laps, %d VSC lap(s).",
        meta["year"], meta["event_name"], meta["round"],
        len(drivers), meta["total_laps"], len(vsc_laps),
    )
    return df, meta


def save_outputs(
    df: pd.DataFrame,
    meta: dict,
    laps_csv: Path = config.LAPS_CSV,
    meta_json: Path = config.META_JSON,
) -> None:
    laps_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(laps_csv, index=False)
    with meta_json.open("w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    log.info("Wrote %s (%d rows) and %s.", laps_csv, len(df), meta_json)


def scrape(
    year: Optional[int] = None,
    round_number: Optional[int] = None,
    reference_date: Optional[pd.Timestamp] = None,
    save: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """End-to-end Stage 1: locate, download, transform and (optionally) persist."""
    session = find_latest_completed_session(
        year=year, round_number=round_number, reference_date=reference_date
    )
    resolved_year = year if year is not None else int(session.event["EventDate"].year)
    df, meta = process_session(session, resolved_year)
    if save:
        save_outputs(df, meta)
    return df, meta


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape the latest completed F1 race.")
    parser.add_argument("--year", type=int, default=None, help="Season (default: auto).")
    parser.add_argument(
        "--round", type=int, default=None, dest="round_number",
        help="Round number (default: latest completed).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = _parse_args(argv)
    scrape(year=args.year, round_number=args.round_number)


if __name__ == "__main__":
    main()
