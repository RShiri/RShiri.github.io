#!/usr/bin/env python3
"""Re-encode the pass stream in matches_detail/*.js — losslessly, ~81% smaller.

WHY. A match file averages 200 KB and 92.6% of that is `passes`. The pass
stream is stored as ~970 JSON objects that each repeat all 15 key names and
spell out six mostly-false booleans:

    {"team":"away","x":49.9,"y":49.9,"ex":23.8,"ey":49.3,"min":0,"sec":0,
     "player":"Mateus Fernandes","recv":null,"ok":true,"key":false,
     "assist":false,"cross":false,"through":false,"prog":false}

Across EPL + La Liga + the three World Cups that is ~602 MB of the 650 MB
corpus, and the repo sits at ~971 MB against GitHub Pages' 1 GB cap. This
converts the stream to a columnar form — one name table, one flag bitmask,
one row array per pass — which measures ~81% smaller with **no information
lost**: `tools/expand_passes.js` (browser) and `expand_passes()` (Python)
reconstruct the original objects field for field.

    {"__c":1,
     "n":["Mateus Fernandes", ...],          # name table, indexed
     "f":["ok","key","assist","cross","through","prog"],
     "r":[[1,49.9,49.9,23.8,49.3,0,0,0,-1,1], ...]}
       #   team x    y    ex   ey   min sec player recv flags

The dashboards do not change: their data files call `__mdExpand(...)`, which
the shim resolves before `window.MATCH_DETAIL` is ever assigned, so
`match.js` still sees exactly the objects it saw before. Python readers are
unaffected too — `corpus.py` slices out the JSON object and never touches
passes; `build_argentina.py` calls expand_passes() first.

    python3 tools/compact_passes.py --check     # report, change nothing
    python3 tools/compact_passes.py --apply     # rewrite in place
    python3 tools/compact_passes.py --revert    # expand back to plain objects
"""
import argparse
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAGS = ["ok", "key", "assist", "cross", "through", "prog"]
CORPORA = [
    "projects/xepl/epl_dashboard/matches_detail",
    "projects/xlaliga/laliga_dashboard/matches_detail",
    "projects/xworldcuptwit/wc2026_dashboard/matches_detail",
    "projects/xworldcuptwit/wc2026_dashboard/editions/2018/matches_detail",
    "projects/xworldcuptwit/wc2026_dashboard/editions/2022/matches_detail",
]
PREFIX = "window.MATCH_DETAIL="
EXPAND_CALL = "window.__mdExpand("


def compact_passes(passes):
    """[{...}, ...] -> the columnar form. Order is preserved exactly."""
    names, index, rows = [], {}, []
    for p in passes:
        for who in (p.get("player"), p.get("recv")):
            if who is not None and who not in index:
                index[who] = len(names)
                names.append(who)
        bits = 0
        for i, key in enumerate(FLAGS):
            if p.get(key):
                bits |= 1 << i
        rows.append([
            0 if p.get("team") == "home" else 1,
            p.get("x"), p.get("y"), p.get("ex"), p.get("ey"),
            p.get("min"), p.get("sec"),
            index.get(p.get("player"), -1),
            index.get(p.get("recv"), -1),
            bits,
        ])
    return {"__c": 1, "n": names, "f": FLAGS, "r": rows}


def expand_passes(block):
    """The exact inverse. Passes straight through if already expanded."""
    if not isinstance(block, dict) or not block.get("__c"):
        return block
    names, flags, out = block["n"], block["f"], []
    for r in block["r"]:
        team, x, y, ex, ey, mn, sec, pi, ri, bits = r
        p = {"team": "home" if team == 0 else "away",
             "x": x, "y": y, "ex": ex, "ey": ey, "min": mn, "sec": sec,
             "player": names[pi] if pi >= 0 else None,
             "recv": names[ri] if ri >= 0 else None}
        for i, key in enumerate(flags):
            p[key] = bool(bits & (1 << i))
        out.append(p)
    return out


def read(path):
    s = open(path, encoding="utf-8").read()
    return s, json.loads(s[s.index("{"):s.rindex("}") + 1])


def write(path, data, compacted):
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if compacted:
        text = "%s%s);\n" % (EXPAND_CALL.replace("window.__mdExpand(",
                                                 "window.MATCH_DETAIL=window.__mdExpand("), body)
    else:
        text = "%s%s;\n" % (PREFIX, body)
    open(path, "w", encoding="utf-8").write(text)


def each_file():
    for corpus in CORPORA:
        d = os.path.join(REPO, corpus)
        if not os.path.isdir(d):
            continue
        for p in sorted(glob.glob(os.path.join(d, "*.js"))):
            if os.path.basename(p) == "_index.js":
                continue
            yield p


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="report savings, change nothing")
    g.add_argument("--apply", action="store_true", help="compact in place")
    g.add_argument("--revert", action="store_true", help="expand back in place")
    args = ap.parse_args()

    before = after = files = touched = 0
    for path in each_file():
        raw, data = read(path)
        files += 1
        before += len(raw.encode())
        passes = data.get("passes")
        is_compact = isinstance(passes, dict) and passes.get("__c")

        if args.revert:
            if not is_compact:
                after += len(raw.encode())
                continue
            data["passes"] = expand_passes(passes)
            write(path, data, compacted=False)
        else:
            if is_compact:
                after += len(raw.encode())
                continue
            packed = compact_passes(passes or [])
            # Never ship a transform that does not round-trip.
            assert expand_passes(packed) == (passes or []), "round-trip failed: " + path
            data["passes"] = packed
            if args.check:
                after += len(json.dumps(data, ensure_ascii=False,
                                        separators=(",", ":")).encode()) + 40
                continue
            write(path, data, compacted=True)
        touched += 1
        after += os.path.getsize(path)

    verb = "would save" if args.check else ("expanded" if args.revert else "saved")
    print("%d files, %d rewritten" % (files, touched))
    print("  %.1f MB -> %.1f MB   (%s %.1f MB, %.1f%%)"
          % (before / 1e6, after / 1e6, verb, (before - after) / 1e6,
             100.0 * (before - after) / before if before else 0))


if __name__ == "__main__":
    main()
