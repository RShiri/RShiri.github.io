#!/usr/bin/env python3
"""Dump each match's real feed as JSON, for the browser replay console.

The live-pipeline page has a console that replays the pipeline's message
stream in the browser: envelopes scroll past, a JS consumer rebuilds match
state from them and prices the 1X2 market with winprob_model.js, and a
"drop the next N messages" control forces the MsgSeq gap that triggers
snapshot recovery.

For that to be honest, the browser must replay the SAME messages the Python
producer emits — not a JavaScript reimplementation of them. So this script
runs the real MatchProducer against a capturing broker and writes the exact
envelopes to assets/data/pipeline/<match_id>.json. The browser is then a
consumer of the pipeline's output, which is the whole point of the demo.

Snapshots are deliberately NOT dumped: the producer is the fixture's
snapshot authority precisely because it holds every message published so
far, and the browser holds the same array, so it rebuilds a snapshot the
same way the producer does.

    python3 live-pipeline/tradepipe/dump_feed.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # live-pipeline/tradepipe/
REPO = HERE.parent.parent                           # rshiri.github.io/
DATA = REPO / "assets" / "data" / "argentina"
OUT = REPO / "assets" / "data" / "pipeline"

sys.path.insert(0, str(HERE.parent))                # live-pipeline/

from tradepipe import get_broker                    # noqa: E402
from tradepipe.messages import MsgType              # noqa: E402
from tradepipe.producer import MatchProducer        # noqa: E402


def capture(match_path):
    """Replay one match and collect every envelope the producer published."""
    broker = get_broker("memory")
    captured = []
    producer = MatchProducer(broker, match_path, quiet=True)
    broker.subscribe("feed.%s" % producer.fixture_id,
                     lambda rk, m: captured.append(m.to_dict()))
    producer.run(instant=True)
    return producer, captured


def build(entry):
    producer, messages = capture(DATA / (entry["id"] + ".json"))
    M = producer.match
    types = {}
    for msg in messages:
        name = msg["Header"]["Type"]
        types[name] = types.get(name, 0) + 1
    return {
        "fixtureId": producer.fixture_id,
        "home": {"name": M["home"]["name"], "color": M["home"].get("color") or "#888"},
        "away": {"name": M["away"]["name"], "color": M["away"].get("color") or "#888"},
        "date": M.get("date"), "stage": M.get("stage") or "",
        "endMin": producer.end_min,
        "settleMin": producer.settle_min,
        "extraTime": producer.has_extra_time,
        "counts": {str(k): v for k, v in sorted(types.items())},
        "messages": messages,
    }


def main():
    idx = json.load(open(DATA / "index.json", encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for entry in idx["matches"]:
        feed = build(entry)
        path = OUT / (feed["fixtureId"] + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(feed, f, ensure_ascii=False, separators=(",", ":"))
        manifest.append({
            "id": feed["fixtureId"],
            "file": "assets/data/pipeline/" + feed["fixtureId"] + ".json",
            "date": feed["date"], "stage": feed["stage"],
            "home": {"name": feed["home"]["name"], "score": entry["home"]["score"]},
            "away": {"name": feed["away"]["name"], "score": entry["away"]["score"]},
            "endMin": feed["endMin"], "settleMin": feed["settleMin"],
            "extraTime": feed["extraTime"],
            "messages": len(feed["messages"]),
        })
        print("%-42s %4d messages  %s  (%.0f KB)"
              % (feed["fixtureId"], len(feed["messages"]),
                 " ".join("t%s:%d" % kv for kv in sorted(feed["counts"].items())),
                 path.stat().st_size / 1024))
    index = {
        "generated_from": "live-pipeline MatchProducer (real TRADE360-style envelopes)",
        "msgTypes": {"1": "FixtureMetadataUpdate", "2": "LivescoreUpdate",
                     "3": "MarketUpdate", "31": "KeepAlive", "35": "Settlement"},
        "matches": manifest,
    }
    with open(OUT / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print("wrote %d feeds + index.json to %s" % (len(manifest), OUT))


if __name__ == "__main__":
    main()
