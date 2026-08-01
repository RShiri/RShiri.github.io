"""Shared configuration and style tokens for the F1Visualized pipeline.

Keeping all paths, palettes and canvas settings in one module means the
scraper, the animator and any *future* live-dashboard front-end can import a
single source of truth instead of duplicating constants. Nothing in here is
tied to a specific race, so the whole pipeline stays modular and scalable.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Filesystem layout
# --------------------------------------------------------------------------- #
ROOT_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = ROOT_DIR / "data"

#: Tidy lap-by-lap table produced by ``scraper.py`` and consumed by ``animator.py``.
LAPS_CSV: Path = DATA_DIR / "race_data.csv"
#: Race/driver metadata (event name, tyre/team colours, VSC laps, ...).
META_JSON: Path = DATA_DIR / "race_meta.json"
#: Position-by-lap timeline animation (Stage 2, animator.py).
OUTPUT_VIDEO: Path = ROOT_DIR / "latest_race_timelapse.mp4"
#: Position-battle race — a line of cars swapping order (race_animator.py).
OUTPUT_REPLAY: Path = ROOT_DIR / "latest_race_replay.mp4"
#: Both views stitched into one synced video (combine_gp_videos.py).
OUTPUT_COMBINED: Path = ROOT_DIR / "latest_race_combined.mp4"

#: fastf1 caches every network request here so re-runs are fast and offline-able.
CACHE_DIR: Path = ROOT_DIR / ".fastf1_cache"

# The F1 live-timing API only exposes rich lap/telemetry data from 2018 onward,
# so that is how far back the "most recent completed race" search will walk.
EARLIEST_SUPPORTED_SEASON: int = 2018

# --------------------------------------------------------------------------- #
# Canvas / theme  (dark-grey surface, recessive grid, high-contrast ink)
# --------------------------------------------------------------------------- #
THEME = {
    "figure_bg": "#15151C",      # near-black dark grey backdrop
    "axes_bg": "#1C1C25",        # slightly lifted panel for depth
    "grid": "#33333F",           # recessive gridlines
    "spine": "#3A3A46",
    "text_primary": "#F4F4F7",   # near-white headline ink
    "text_secondary": "#9B9BA6",  # muted axis / caption ink
    "vsc": "#FFD400",            # flashing Virtual Safety Car banner
    "pit": "#22C55E",            # green [IN PIT] tag
    "accent": "#E10600",         # F1 brand red
}

# --------------------------------------------------------------------------- #
# Tyre compounds — colour + single-letter badge (identity by colour AND letter)
# --------------------------------------------------------------------------- #
COMPOUNDS = {
    "SOFT":         {"letter": "S", "color": "#DA291C", "text": "#FFFFFF"},
    "MEDIUM":       {"letter": "M", "color": "#F6D200", "text": "#15151C"},
    "HARD":         {"letter": "H", "color": "#EDEDED", "text": "#15151C"},
    "INTERMEDIATE": {"letter": "I", "color": "#43B02A", "text": "#FFFFFF"},
    "WET":          {"letter": "W", "color": "#0067AD", "text": "#FFFFFF"},
    "UNKNOWN":      {"letter": "?", "color": "#6E6E7A", "text": "#FFFFFF"},
}


# --------------------------------------------------------------------------- #
# Position-battle race tokens (a line of cars swapping order)
# --------------------------------------------------------------------------- #
RACE = {
    "lane": "#26262F",         # faint per-position lane guide
    "lane_alt": "#202027",     # alternating lane band
    "finish": "#EDEDF2",       # finish line
}
CAR_MARKER_SIZE = 30           # points; car sprite size


def car_marker():
    """A top-view open-wheel F1 car silhouette Path (nose pointing +x).

    A compound Path: the chassis (nose + front/rear wings + body) plus four
    outboard wheels drawn as separate blocks with a gap to the body, so it reads
    unmistakably as an open-wheel car. Usable as a matplotlib plot/scatter marker
    — every driver becomes a real little car that slides between positions.
    """
    from matplotlib.path import Path as _Path

    # Chassis: nose (+x) -> front wing -> body -> rear wing -> mirror back.
    chassis = [
        (1.00, 0.00), (0.80, 0.075), (0.70, 0.075), (0.70, 0.34), (0.61, 0.34),
        (0.61, 0.075), (0.30, 0.10), (-0.20, 0.12), (-0.62, 0.13), (-0.82, 0.15),
        (-0.82, 0.42), (-0.92, 0.42), (-0.92, -0.42), (-0.82, -0.42), (-0.82, -0.15),
        (-0.62, -0.13), (-0.20, -0.12), (0.30, -0.10), (0.61, -0.075), (0.61, -0.34),
        (0.70, -0.34), (0.70, -0.075), (0.80, -0.075), (1.00, 0.00),
    ]

    def _wheel(x0, x1, y0, y1):
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]

    wheels = [
        _wheel(0.28, 0.55, 0.22, 0.44),    # front-left
        _wheel(0.28, 0.55, -0.44, -0.22),  # front-right
        _wheel(-0.72, -0.45, 0.24, 0.47),  # rear-left
        _wheel(-0.72, -0.45, -0.47, -0.24),  # rear-right
    ]

    verts, codes = [], []
    for sub in [chassis, *wheels]:
        verts.extend(sub)
        codes += [_Path.MOVETO] + [_Path.LINETO] * (len(sub) - 2) + [_Path.CLOSEPOLY]
    return _Path(verts, codes)


def compound_style(compound: str) -> dict:
    """Return the badge style for a compound, tolerant of casing / aliases."""
    if not isinstance(compound, str):
        return COMPOUNDS["UNKNOWN"]
    key = compound.strip().upper()
    aliases = {"INTER": "INTERMEDIATE", "WETS": "WET", "": "UNKNOWN", "NAN": "UNKNOWN"}
    key = aliases.get(key, key)
    return COMPOUNDS.get(key, COMPOUNDS["UNKNOWN"])


# --------------------------------------------------------------------------- #
# Fallback team palette
# --------------------------------------------------------------------------- #
# fastf1 normally supplies a per-driver ``TeamColor``. When that is missing
# (e.g. metadata failed to load for a very fresh session) we deal out these
# visually distinct hues so every driver still gets a stable, unique colour.
FALLBACK_TEAM_COLORS = [
    "#00D2BE", "#DC0000", "#0600EF", "#FF8700", "#006F62",
    "#005AFF", "#900000", "#2B4562", "#FFFFFF", "#00A3E0",
    "#B6BABD", "#FF87BC", "#52E252", "#C8102E", "#6692FF",
    "#F91536", "#37BEDD", "#358C75", "#3671C6", "#64C4FF",
]
