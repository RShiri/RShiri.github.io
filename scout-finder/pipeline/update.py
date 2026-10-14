"""Weekly refresh: fetch the current season's new matches and players, rebuild, push.

  python -m pipeline.update                 # fetch + build, no git
  python -m pipeline.update --push          # ... then commit and push data/ on this branch

Run from a scheduled task on Ram's machine (the cloud cannot reach FotMob).
Only matches and players not cached yet hit the network, so a weekly run is a
few hundred requests. The build covers every season with fetched CSVs.
"""
from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

from . import fetch_fotmob, fetch_players
from .leagues import LEAGUES

ROOT = Path(__file__).resolve().parent.parent
ELO_DATE = "2026-05-31"


def current_season(today: datetime.date | None = None) -> str:
    """The season turns over on 1 July: 2026-10-15 -> '2026-27'."""
    today = today or datetime.date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start}-{str(start + 1)[2:]}"


def run(*args: str) -> None:
    print("$", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def push() -> None:
    files = ["data/seasons.json"] + [str(p.relative_to(ROOT)) for p in
                                     sorted((ROOT / "data").glob("universe_*.json"))]
    run("git", "add", *files)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        print("nothing changed")
        return
    stamp = datetime.date.today().isoformat()
    run("git", "commit", "-m", f"[Scout Finder] weekly update ({current_season()}, {stamp})")
    run("git", "pull", "--rebase", "-q")
    # gh holds the GitHub login on this machine; Git Credential Manager would
    # open a window that a scheduled task cannot answer.
    run("git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
        "push", "-q")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default=None, help="default: the current season")
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()
    season = a.season or current_season()
    for code in sorted(LEAGUES):
        try:
            fetch_fotmob.fetch_league(code, season)
        except Exception as exc:           # one league down must not stop the rest
            print(f"! {code} {season}: {exc}")
    sys.argv = ["fetch_players"]
    fetch_players.main()
    run(sys.executable, "-m", "pipeline.build", "--fotmob", "--elo-date", ELO_DATE)
    if a.push:
        push()


if __name__ == "__main__":
    main()
