"""One row per player per season, whatever the source.

Every source adapter returns a DataFrame with the ID/context columns below plus
any of the stat columns it can fill. Stats are season TOTALS; per-90 rates and
percentiles are derived later in build.py, so adapters never do maths.
"""

ID_COLS = [
    "source",      # "understat" | "fotmob"
    "season",      # "2025-26"
    "league",      # "EPL"
    "player_id",   # source-native id, namespaced: "fotmob:315227", "understat:8260"
    "name",
    "team",
    "pos_group",   # GK | CB | FB | DM | CM | AM | W | FW (see positions.py)
    "matches",
    "minutes",
]

# Season totals. A source leaves a column out when it does not publish it.
STAT_COLS = [
    "goals", "assists",
    "xg", "npxg", "xa",
    "shots", "shots_on_target",
    "key_passes",
    "passes", "passes_accurate",
    "touches",
    "dribbles",          # successful take-ons
    "tackles", "interceptions", "clearances",
    "aerials_won",
    "dispossessed",
    "xg_chain", "xg_buildup",  # Understat only: involvement in possessions ending in a shot
    "saves",
]

# Which source fills which stat, so the site can say where each number came from.
SOURCE_COVERAGE = {
    "understat": {"goals", "assists", "xg", "npxg", "xa", "shots", "key_passes",
                  "xg_chain", "xg_buildup"},
    "fotmob": {"goals", "assists", "xg", "xa", "shots", "shots_on_target", "key_passes",
               "passes", "passes_accurate", "touches", "dribbles", "tackles",
               "interceptions", "clearances", "aerials_won", "dispossessed", "saves"},
}
