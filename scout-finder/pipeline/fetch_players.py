"""Player profiles from FotMob: height, foot, birth date, contract end, current value.

  python -m pipeline.fetch_players               # every player in data/fotmob/*.csv
  python -m pipeline.fetch_players --min-minutes 300

One playerData request per player, cached (trimmed) under
data/raw/fotmob_players/<id>.json, same politeness as the match fetcher. The
profile is FotMob's as of the fetch day: current club, current value, current
contract. build.py merges it into every season's players as height, foot,
contract_end, birth_date, value_eur (the lineup value from the season itself is
kept when there is no profile).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
from pathlib import Path

from .fetch_fotmob import DATA, PAUSE, _get

RAW = DATA / "raw" / "fotmob_players"
OUT = DATA / "players.json"
# Enough of the response to rebuild everything below without re-fetching.
KEEP = ("id", "name", "birthDate", "contractEnd", "primaryTeam", "positionDescription",
        "playerInformation", "traits", "marketValues")


def player_details(pid: int) -> dict:
    cache = RAW / f"{pid}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    time.sleep(random.uniform(*PAUSE))
    data = _get(f"/playerData?id={pid}")
    trimmed = {k: data.get(k) for k in KEEP}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(trimmed, ensure_ascii=False), encoding="utf-8")
    return trimmed


def _info(d: dict) -> dict:
    """playerInformation rows -> {translationKey: value}."""
    out = {}
    for row in d.get("playerInformation") or []:
        v = row.get("value") or {}
        out[row.get("translationKey")] = v.get("numberValue", v.get("key") or v.get("fallback"))
    return out


def profile(d: dict) -> dict:
    """The fields the page uses, from one trimmed playerData response."""
    info = _info(d)
    pos = d.get("positionDescription") or {}
    main = next((p for p in pos.get("positions") or [] if p.get("isMainPosition")), None)
    team = d.get("primaryTeam") or {}
    out = {
        "height": info.get("height_sentencecase"),
        "foot": info.get("preferred_foot"),
        "value_eur": info.get("transfer_value"),
        "birth_date": ((d.get("birthDate") or {}).get("utcTime") or "")[:10] or None,
        "contract_end": ((d.get("contractEnd") or {}).get("utcTime") or "")[:10] or None,
        "current_team": team.get("teamName"),
        "on_loan": team.get("onLoan"),
        # FotMob's own reading of the player's career positions, e.g. "Defensive Midfielder".
        "main_position": (pos.get("primaryPosition") or {}).get("key"),
        "main_position_id": int(main["position"]) if main and main.get("position") else None,
    }
    return {k: v for k, v in out.items() if v not in (None, "")}


def player_ids(min_minutes: int) -> list[int]:
    """Players with at least min_minutes in any league-season fetched so far."""
    minutes: dict[tuple[str, str, int], float] = {}
    for path in sorted((DATA / "fotmob").glob("*.csv")):
        with path.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                key = (r["league"], r["season"], int(r["player_id"]))
                minutes[key] = minutes.get(key, 0) + float(r["minutes"] or 0)
    keep = {pid for (_, _, pid), m in minutes.items() if m >= min_minutes}
    return sorted(keep)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-minutes", type=int, default=300,
                    help="skip players below this in every league-season (default 300)")
    a = ap.parse_args()
    ids = player_ids(a.min_minutes)
    print(f"{len(ids)} players, {sum((RAW / f'{i}.json').exists() for i in ids)} cached")
    profiles, failed = {}, []
    for n, pid in enumerate(ids, 1):
        try:
            profiles[str(pid)] = profile(player_details(pid))
        except Exception as exc:  # one bad player must not sink the run
            failed.append(pid)
            print(f"  ! {pid}: {exc}")
        if n % 100 == 0:
            print(f"  {n}/{len(ids)}")
    OUT.write_text(json.dumps(profiles, ensure_ascii=False), encoding="utf-8")
    print(f"{len(profiles)} profiles -> {OUT} ({len(failed)} failed)")


if __name__ == "__main__":
    main()
