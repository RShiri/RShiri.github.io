#!/usr/bin/env python3
"""Multi-corpus loader for the win-probability model.

Ram's scrapers write one `window.MATCH_DETAIL = {...}` JS file per match,
all sharing one schema, across five corpora:

    EPL      <XEPL>/epl_dashboard/matches_detail/*.js            (4 seasons)
    La Liga  <XLALIGA>/laliga_dashboard/matches_detail/*.js      (4 seasons)
    WC 2026  <XWORLDCUPTWIT>/wc2026_dashboard/matches_detail/*.js
    WC 2018  <XWORLDCUPTWIT>/wc2026_dashboard/editions/2018/matches_detail/*.js
    WC 2022  <XWORLDCUPTWIT>/wc2026_dashboard/editions/2022/matches_detail/*.js

This module turns those files into normalized match dicts the calibrator
can consume. Two hard-won rules live here:

  * Competition NEVER comes from the "stage" string — the La Liga scraper
    left "Group Stage" in every file (a template leftover) and the WC files
    mix "Group Stage" / "Group I" / "World Cup Grp. A" / "" freely.
    Competition comes from which directory the file was loaded from.
  * has_extra_time is True only for World Cup knockout matches that
    ACTUALLY played extra time (knockout_played_extra_time below — maxMin
    is decisive when present). League matches, WC group games, and WC
    knockouts settled in regulation end at 90' + stoppage, so their events
    past minute 90 fold into minute 90 for the 1X2 market
    (model.effective_min). A knockout decided by a stoppage-time winner is
    NOT an extra-time match: 90+1' counts toward the 90' market exactly
    like group-stage stoppage.
"""
import json
import re
from pathlib import Path

# id fragments that mark a knockout file scraped before the real fixture
# was known: "Winner_QF_3", "Loser_SF_1", "1J_vs_2H", "2A_vs_2B", ...
_PLACEHOLDER_ID = re.compile(r"Winner_|Loser_|_\d[A-L]\d?_vs|_vs_\d[A-L]\d?")


def parse_match_detail(path):
    """One matches_detail/*.js file -> the raw match dict. The files are
    `window.MATCH_DETAIL = {...};` so we slice out the JSON object."""
    s = Path(path).read_text(encoding="utf-8")
    return json.loads(s[s.index("{"):s.rindex("}") + 1])


def league_season(date):
    """"2023-11-04" -> "2023-24". European league seasons run Aug-May, so
    Jan-Jul dates belong to the season that STARTED the previous year."""
    year, month = int(date[:4]), int(date[5:7])
    start = year if month >= 8 else year - 1
    return "%d-%02d" % (start, (start + 1) % 100)


def is_groupish(stage):
    """True for any group-phase stage label ("Group Stage", "Group I",
    "World Cup Grp. A", ...)."""
    s = (stage or "").lower()
    return "group" in s or "grp" in s


def has_shootout_evidence(raw):
    """True when the file records a penalty shootout: home/away pens
    non-null, or a non-empty shootout array. Shootouts only happen after
    extra time in a knockout, so this evidence is unambiguous."""
    if (raw.get("home") or {}).get("pens") is not None:
        return True
    if (raw.get("away") or {}).get("pens") is not None:
        return True
    return bool(raw.get("shootout"))


def wc_is_knockout(raw):
    """Was this WC match a knockout tie? Stage label first — EXCEPT that
    penalty-shootout evidence always wins: a shootout cannot happen in a
    group game, and one WC2026 R32 file (2026_06_29_1E_vs_3ABCDF, pens
    3-4) kept the scraper's "Group Stage" template stage. An empty stage
    (one WC2026 file has stage="" AND date="") is knockout only if the
    date falls in the WC2026 knockout window (from 2026-06-29)."""
    if has_shootout_evidence(raw):
        return True
    stage = raw.get("stage") or ""
    if is_groupish(stage):
        return False
    if not stage.strip():
        date = raw.get("date") or ""
        return bool(date) and date >= "2026-06-29"
    return True


def knockout_played_extra_time(raw):
    """Did this KNOCKOUT match actually play extra time? Decided per match,
    in priority order:

      1. maxMin (last minute on the match clock, present in every
         /workspace matches_detail file): >= 115 => extra time was played.
         ET always reaches 120' (recorded 120-131 with its own stoppage),
         while regulation with long stoppage tops out around 108 in this
         data - nothing legitimate lives in 109..119, so 115 splits the
         two clusters. < 115 => no ET.
      2. Penalty-shootout evidence (pens / shootout) => ET.
      3. Any recorded event (shot or goal) with min > 95 => ET.
      4. Otherwise fold events at 91..95 into minute 90 (second-half
         stoppage). A LEVEL folded 90' score => ET (a level knockout must
         have played it; its events just weren't recorded past 90'). A
         decided score => no ET: a regulation win via a stoppage-time
         goal, which settles the 90' market like any stoppage goal.
    """
    max_min = raw.get("maxMin")
    if max_min is not None:
        return max_min >= 115
    if has_shootout_evidence(raw):
        return True
    ev_mins = ([s["min"] for s in raw.get("shots") or []]
               + [g["min"] for g in raw.get("goals") or []])
    if any(m > 95 for m in ev_mins):
        return True
    h = a = 0
    for g in raw.get("goals") or []:
        if g["min"] <= 95:                   # 91..95 folds into minute 90
            if g["team"] == "home":
                h += 1
            else:
                a += 1
    return h == a


def wc_has_extra_time(raw):
    """has_extra_time for a raw WC match dict: knockouts that actually
    played extra time. Group games never play it."""
    return wc_is_knockout(raw) and knockout_played_extra_time(raw)


def normalize(raw, competition, edition=None):
    """Raw MATCH_DETAIL dict -> the normalized match dict the model uses.

    90-minute xG per side is summed from the shot stream on the market
    clock: stoppage-time shots fold into minute 90, extra-time shots (WC
    knockouts that actually played ET) are excluded — there is no
    top-level xg field in these corpora (unlike the argentina JSONs)."""
    stage = raw.get("stage") or ""
    date = raw.get("date") or ""
    if competition == "WC":
        season = str(edition)
        has_et = wc_has_extra_time(raw)
        is_neutral = True
    else:
        season = league_season(date)
        has_et = False                       # leagues never play extra time
        is_neutral = False
    xg = [0.0, 0.0]
    for s in raw.get("shots") or []:
        m = _eff_min(s["min"], has_et)
        if m is not None:
            xg[0 if s["team"] == "home" else 1] += s["xg"]
    return {
        "competition": competition,
        "season": season,
        "stage": stage,
        "date": date,
        "home": raw["home"]["name"],
        "away": raw["away"]["name"],
        "shots": raw.get("shots") or [],
        "goals": raw.get("goals") or [],
        "has_extra_time": has_et,
        "is_neutral": is_neutral,
        "xg": xg,
    }


def _eff_min(event_min, has_extra_time):
    """Local copy of model.effective_min so corpus.py stays standalone."""
    if event_min <= 90:
        return event_min
    return None if has_extra_time else 90


def load_dir(dir_path, competition, edition=None, dedup=False):
    """All matches in one matches_detail/ directory, normalized and sorted
    by filename. dedup=True (WC2026) collapses files describing the same
    (date, home, away) fixture — the scraper left placeholder-id knockout
    files ("Winner_EF_5_vs_...") duplicating the real ones — preferring
    the file whose id is NOT a placeholder."""
    dir_path = Path(dir_path)
    entries = []                             # (fname, raw) in filename order
    for p in sorted(dir_path.glob("*.js")):
        if p.name == "_index.js":
            continue
        entries.append((p.stem, parse_match_detail(p)))
    if dedup:
        by_key = {}
        for stem, raw in entries:
            key = (raw.get("date") or "", raw["home"]["name"], raw["away"]["name"])
            prev = by_key.get(key)
            if prev is None:
                by_key[key] = (stem, raw)
            elif _PLACEHOLDER_ID.search(prev[0]) and not _PLACEHOLDER_ID.search(stem):
                by_key[key] = (stem, raw)    # real id beats placeholder id
        dropped = len(entries) - len(by_key)
        entries = sorted(by_key.values())
        if dropped:
            print("  (deduped %d placeholder/duplicate WC files)" % dropped)
    return [normalize(raw, competition, edition) for _, raw in entries]


def iter_matches(corpora):
    """Yield normalized matches for `corpora`, a list of
    (competition, matches_detail_dir, edition) tuples — edition is the WC
    year for "WC" entries, None for leagues. Prints per-corpus counts."""
    for competition, dir_path, edition in corpora:
        label = competition if edition is None else "%s %s" % (competition, edition)
        matches = load_dir(dir_path, competition, edition,
                           dedup=(competition == "WC"))
        print("loaded %-8s %4d matches  (%s)" % (label, len(matches), dir_path))
        for M in matches:
            yield M


def default_corpora(epl=None, laliga=None, wc=None, repo_root=None):
    """Resolve the corpus roots into (competition, dir, edition) tuples.

    Roots default to sibling clones of the scraper repos (../XEPL etc.,
    the same convention build_argentina.py uses), falling back to
    /workspace/<name> where the CI environment clones them. Corpora whose
    root is missing are silently skipped — calibrate.py warns if NOTHING
    is found and falls back to the 8 argentina files."""
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent.parent

    def resolve(explicit, *candidates):
        if explicit:
            return Path(explicit)
        for c in candidates:
            if Path(c).is_dir():
                return Path(c)
        return None

    epl_root = resolve(epl, repo_root.parent / "XEPL", "/workspace/xepl")
    laliga_root = resolve(laliga, repo_root.parent / "XLALIGA", "/workspace/xlaliga")
    wc_root = resolve(wc, repo_root.parent / "XWORLDCUPTWIT", "/workspace/xworldcuptwit")

    corpora = []
    if epl_root and (epl_root / "epl_dashboard" / "matches_detail").is_dir():
        corpora.append(("EPL", epl_root / "epl_dashboard" / "matches_detail", None))
    if laliga_root and (laliga_root / "laliga_dashboard" / "matches_detail").is_dir():
        corpora.append(("LaLiga", laliga_root / "laliga_dashboard" / "matches_detail", None))
    if wc_root:
        dash = wc_root / "wc2026_dashboard"
        for edition, sub in ((2018, dash / "editions" / "2018" / "matches_detail"),
                             (2022, dash / "editions" / "2022" / "matches_detail"),
                             (2026, dash / "matches_detail")):
            if sub.is_dir():
                corpora.append(("WC", sub, edition))
    return corpora, {"EPL": epl_root, "LaLiga": laliga_root, "WC": wc_root}
