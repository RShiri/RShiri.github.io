"""Snapshot contract shared by producer (build) and consumer (parse).

A snapshot is the RPC reply a late-joining or gapped consumer gets from the
feed's snapshot authority (the producer). It carries everything needed to
rebuild MatchState mid-match:

    {"FixtureId": "<id>",
     "Fixture": {...last published fixture metadata...},
     "Livescore": {"Scoreboard": {...}, "Statistics": [...],
                   "Incidents": [ALL incidents published so far]},
     "LastMsgSeq": <seq of the last message the producer published>}

Both sides go through this module so the payload shape lives in one place.
"""


def build_snapshot(fixture_id, fixture, scoreboard, statistics, incidents, last_seq):
    """Producer side: pack the current replay state into a snapshot payload."""
    return {
        "FixtureId": fixture_id,
        "Fixture": dict(fixture) if fixture else {},
        "Livescore": {
            "Scoreboard": dict(scoreboard) if scoreboard else {},
            "Statistics": [dict(s) for s in (statistics or [])],
            "Incidents": [dict(i) for i in (incidents or [])],
        },
        "LastMsgSeq": int(last_seq),
    }


def parse_snapshot(payload):
    """Consumer side: unpack a snapshot payload into plain fields."""
    live = payload.get("Livescore") or {}
    return {
        "fixture_id": payload.get("FixtureId"),
        "fixture": payload.get("Fixture") or {},
        "scoreboard": live.get("Scoreboard") or {},
        "statistics": live.get("Statistics") or [],
        "incidents": live.get("Incidents") or [],
        "last_seq": payload.get("LastMsgSeq", 0),
    }
