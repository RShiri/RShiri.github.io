#!/usr/bin/env python3
"""Build the offline win-probability timelines for rshiri.github.io.

For every Argentina match in assets/data/argentina/index.json this replays
the recorded match through the mini-TRADE360 pipeline — MatchProducer ->
InMemoryBroker -> TradeConsumer — instantly and deterministically, then
writes the consumer's 91-row minute-by-minute timeline (win/draw/win
probabilities, fair odds, cumulative xG, score, shot/goal events) to
assets/data/winprob/<match_id>.json, plus an index.json manifest that
mirrors the argentina one and carries the model constants.

Re-run after new matches are scraped (build_argentina.py output changed)
or after the model is refit (calibrate.py rewrote model_params.json):

    python3 live-pipeline/tradepipe/build_timelines.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # live-pipeline/tradepipe/
REPO = HERE.parent.parent                           # rshiri.github.io/
DATA = REPO / "assets" / "data" / "argentina"
OUT = REPO / "assets" / "data" / "winprob"

sys.path.insert(0, str(HERE.parent))                # live-pipeline/

from tradepipe import get_broker                    # noqa: E402
from tradepipe.producer import MatchProducer        # noqa: E402
from tradepipe.consumer import TradeConsumer        # noqa: E402


def replay_match(match_path):
    """Run the instant in-memory pipeline for one match; return (producer,
    consumer) after full time + settlement."""
    broker = get_broker("memory")
    producer = MatchProducer(broker, match_path, quiet=True)
    consumer = TradeConsumer(broker, producer.fixture_id, quiet=True)
    producer.run(instant=True)
    return producer, consumer


def build_timeline(entry):
    """Replay one manifest entry -> the winprob/<id>.json dict."""
    producer, consumer = replay_match(DATA / (entry["id"] + ".json"))
    M = producer.match
    model = consumer.model                          # holds the prematch lams
    row0 = consumer.timeline[0]                     # minute-0 (prematch) probs
    return {
        "id": entry["id"],
        "home": {"name": M["home"]["name"], "color": M["home"].get("color") or "#888"},
        "away": {"name": M["away"]["name"], "color": M["away"].get("color") or "#888"},
        "date": M.get("date"), "stage": M.get("stage") or "",
        "final": {"scoreH": consumer.state.score_h, "scoreA": consumer.state.score_a,
                  "settled": consumer.settlement_result},
        "prematch": {"lamH": round(model.lam_h, 6), "lamA": round(model.lam_a, 6),
                     "pH": row0["pH"], "pD": row0["pD"], "pA": row0["pA"]},
        "timeline": consumer.timeline,
    }


def main():
    idx = json.load(open(DATA / "index.json", encoding="utf-8"))
    params = json.load(open(OUT / "model_params.json", encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    manifest = []
    for entry in idx["matches"]:
        T = build_timeline(entry)
        out_path = OUT / (T["id"] + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(T, f, ensure_ascii=False, separators=(",", ":"))
        manifest.append({
            "id": T["id"],
            "file": "assets/data/winprob/" + T["id"] + ".json",
            "date": T["date"], "stage": T["stage"],
            "home": {"name": entry["home"]["name"], "score": entry["home"]["score"]},
            "away": {"name": entry["away"]["name"], "score": entry["away"]["score"]},
        })
        print("%-42s final %d-%d ('%s') | 0' P %.3f/%.3f/%.3f | %d rows"
              % (T["id"], T["final"]["scoreH"], T["final"]["scoreA"],
                 T["final"]["settled"], T["prematch"]["pH"], T["prematch"]["pD"],
                 T["prematch"]["pA"], len(T["timeline"])))

    index = {
        "generated_from": "live-pipeline (mini-TRADE360 replay)",
        "model": {"mu": params["mu"], "w": params["w"], "k": params["k"],
                  "hfa": params.get("hfa", 1.0),
                  "version": params.get("version", 1)},
        "matches": manifest,
    }
    with open(OUT / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print("wrote %d timelines + index.json" % len(manifest))


if __name__ == "__main__":
    main()
