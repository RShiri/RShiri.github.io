#!/usr/bin/env python3
"""Terminal demo of the mini-TRADE360 pipeline: replay one recorded match
as a live feed (producer) and price it in real time (consumer).

    python3 run_demo.py --list
    python3 run_demo.py --match 2026_06_17_Argentina_vs_Algeria --speed 600
    python3 run_demo.py --match 2026_07_04_1J_vs_2H --speed 600 --late-join 60
    python3 run_demo.py --match ... --broker rabbit --rabbit-url amqp://...

speed is simulated-minutes per real minute: 60 = real time-ish (1 s/min),
600 = whole match in ~9 s. --late-join N attaches the consumer only from
minute N, which forces a MsgSeq gap and a snapshot recovery — the point of
the demo. Memory mode is a single process; rabbit mode runs the consumer's
connection in a daemon thread (needs a local RabbitMQ + pip install pika).
"""
import argparse
import json
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent            # live-pipeline/
REPO = HERE.parent
DATA = REPO / "assets" / "data" / "argentina"

sys.path.insert(0, str(HERE))

from tradepipe import get_broker                  # noqa: E402
from tradepipe.producer import MatchProducer      # noqa: E402
from tradepipe.consumer import TradeConsumer      # noqa: E402


def load_index():
    with open(DATA / "index.json", encoding="utf-8") as f:
        return json.load(f)


def list_matches():
    for m in load_index()["matches"]:
        print("%-42s %s  %-12s %s %d-%d %s"
              % (m["id"], m["date"], m["stage"], m["home"]["name"],
                 m["home"]["score"], m["away"]["score"], m["away"]["name"]))


def summary(producer, consumer):
    h, a = producer.score_at(90)
    actual = "1" if h > a else ("X" if h == a else "2")
    print()
    print("=== summary ===============================================")
    print("actual 90' result: %d-%d ('%s')" % (h, a, actual))
    if producer.has_extra_time:
        fh, fa = producer.score_raw_at(producer.end_min)
        print("after extra time: %d-%d at %d' (1X2 market settled on the 90' score)"
              % (fh, fa, producer.end_min))
    elif producer.end_min > 90:
        print("final whistle at 90+%d'" % (producer.end_min - 90))
    if consumer is not None and consumer.timeline:
        last = consumer.timeline[-1]
        print("final model probs: H %.3f / D %.3f / A %.3f (at %d')"
              % (last["pH"], last["pD"], last["pA"], last["min"]))
    if consumer is not None:
        print("messages: producer published %d, consumer received %d, "
              "markets published %d, timeline rows %d, recoveries %d"
              % (producer.messages_published, consumer.messages_received,
                 consumer.markets_published, len(consumer.timeline),
                 consumer.recoveries))
        if consumer.settlement_result:
            print("settled: '%s'" % consumer.settlement_result)


def run_memory(args, match_path):
    broker = get_broker("memory")
    producer = MatchProducer(broker, match_path, speed=args.speed)
    consumer = None
    if not args.late_join:
        consumer = TradeConsumer(broker, producer.fixture_id)
    delay = 60.0 / args.speed
    for t in producer.replay():
        if args.late_join and consumer is None and t == args.late_join - 1:
            print("[consumer] joined at minute %d" % args.late_join)
            consumer = TradeConsumer(broker, producer.fixture_id)
        if delay > 0 and t < producer.end_min:
            time.sleep(delay)
    summary(producer, consumer)


def run_rabbit(args, match_path):
    # Two connections: pika channels are not thread-safe, so the producer
    # publishes (and serves snapshots) on one, the consumer consumes on
    # another running in a daemon thread.
    pub = get_broker("rabbit", url=args.rabbit_url)
    sub = get_broker("rabbit", url=args.rabbit_url)
    producer = MatchProducer(pub, match_path, speed=args.speed)
    consumer = None
    if not args.late_join:
        consumer = TradeConsumer(sub, producer.fixture_id)
        threading.Thread(target=sub.start, daemon=True).start()
    delay = 60.0 / args.speed
    for t in producer.replay():
        if args.late_join and consumer is None and t == args.late_join - 1:
            print("[consumer] joined at minute %d" % args.late_join)
            consumer = TradeConsumer(sub, producer.fixture_id)
            threading.Thread(target=sub.start, daemon=True).start()
        # process_data_events on the producer connection also serves
        # snapshot RPC requests while pacing the replay
        producer._sleep(max(delay, 0.001) if t < producer.end_min else 0.5)
    time.sleep(0.5)                        # let the consumer thread drain
    summary(producer, consumer)
    sub.close()
    pub.close()


def main():
    ap = argparse.ArgumentParser(description="Replay a match as a live feed and price it in-play.")
    ap.add_argument("--match", help="match id, e.g. 2026_06_17_Argentina_vs_Algeria")
    ap.add_argument("--speed", type=float, default=60.0,
                    help="simulated minutes per real minute (600 = match in ~9 s)")
    ap.add_argument("--broker", choices=["memory", "rabbit"], default="memory")
    ap.add_argument("--rabbit-url", default="amqp://guest:guest@localhost:5672/%2F")
    ap.add_argument("--late-join", type=int, default=0, metavar="N",
                    help="attach the consumer only from minute N (snapshot recovery demo)")
    ap.add_argument("--list", action="store_true", help="list available match ids")
    args = ap.parse_args()

    if args.list:
        list_matches()
        return
    if not args.match:
        ap.error("--match is required (use --list to see the available ids)")
    match_path = DATA / (args.match + ".json")
    if not match_path.exists():
        print("unknown match %r; available:" % args.match)
        list_matches()
        sys.exit(1)
    if not 0 <= args.late_join <= 90:
        ap.error("--late-join must be between 0 and 90")

    if args.broker == "memory":
        run_memory(args, match_path)
    else:
        run_rabbit(args, match_path)


if __name__ == "__main__":
    main()
