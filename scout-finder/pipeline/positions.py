"""Map every source's position labels onto one set of eight groups.

Percentiles only mean something inside a group: a centre-back's 40 passes a game
is ordinary, a striker's is not.
"""

GROUPS = ["GK", "CB", "FB", "DM", "CM", "AM", "W", "FW"]

# WhoScored-style slot codes, as FotMob/XEPL lineups store them.
SLOT_TO_GROUP = {
    "GK": "GK",
    "DC": "CB",
    "DR": "FB", "DL": "FB", "DMR": "FB", "DML": "FB",
    "DMC": "DM",
    "MC": "CM", "MR": "W", "ML": "W",
    "AMC": "AM",
    "AMR": "W", "AML": "W", "FWR": "W", "FWL": "W",
    "FW": "FW",
}

# Understat season position strings are space-separated codes, most-played first,
# e.g. "F M S" or "D S". It is coarse (no CB/FB split), so we pick the closest group.
UNDERSTAT_TO_GROUP = {"GK": "GK", "D": "CB", "M": "CM", "F": "FW"}


def group_from_slot(slot: str) -> str | None:
    return SLOT_TO_GROUP.get((slot or "").strip().upper())


def group_from_understat(position: str) -> str | None:
    for code in (position or "").split():
        if code in UNDERSTAT_TO_GROUP:
            return UNDERSTAT_TO_GROUP[code]
    return None
