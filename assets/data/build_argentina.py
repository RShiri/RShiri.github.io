#!/usr/bin/env python3
"""Generate the Argentina Match Centre data for rshiri.github.io.

Reads the WC2026 pipeline output from the sibling XWORLDCUPTWIT repo
(`wc2026_dashboard/matches_detail/<id>.js` for the event stream + lineups,
and `wc2026/matches/<id>.json` for FotMob aggregate stats) and emits one
self-contained JSON per Argentina match in the shape `main.js` expects, plus
an `index.json` manifest that drives the match picker.

Per match the output carries: scoreboard (home/away/score/colour/xG), a
head-to-head stat panel, a two-team shot map, and pass-by-pass goal replays.
The replay build-up reconstruction is a straight port of the dashboard's
`buildGoalSequences()` (match.js), so the native page agrees with the full
WC2026 match centre by construction.

Manual run (XWORLDCUPTWIT auto-detected as a sibling checkout):
    python3 assets/data/build_argentina.py

From the XWORLDCUPTWIT auto-deploy (source + output given explicitly):
    python3 build_argentina.py --source <XWORLDCUPTWIT root> --out <clone>/assets/data/argentina

Sources may also come from the env: WC_SOURCE (XWORLDCUPTWIT root), WC_OUT (output dir).
"""
import argparse
import json
import os
import glob
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))          # rshiri.github.io/

TEAM = "Argentina"


def resolve_source(explicit=None):
    """Locate the XWORLDCUPTWIT checkout: explicit arg → WC_SOURCE env → sibling."""
    for cand in (explicit, os.environ.get("WC_SOURCE"),
                 os.path.join(os.path.dirname(REPO), "XWORLDCUPTWIT"),
                 os.path.join(REPO, "..", "XWORLDCUPTWIT")):
        if cand and os.path.isdir(cand):
            return os.path.abspath(cand)
    raise SystemExit("XWORLDCUPTWIT source not found (pass --source or set WC_SOURCE)")


def norm(s):
    """Accent-fold + lowercase, matching match.js agmNorm."""
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def agmT(o):
    return (o.get("min") or 0) * 60 + (o.get("sec") or 0)


def load_detail(path):
    s = open(path, encoding="utf-8").read()
    return json.loads(s[s.index("{"):].rstrip().rstrip(";"))


def num_map(D):
    """player -> shirt number, from both lineups (starters + subs)."""
    m = {}
    for sd in ("home", "away"):
        lu = (D.get("lineups") or {}).get(sd) or {}
        for p in (lu.get("starters") or []) + (lu.get("subs") or []):
            if p and p.get("name") is not None and p.get("num") is not None:
                m[norm(p["name"])] = p["num"]
    return m


def assist_for(D, shot):
    for g in D.get("goals") or []:
        if g["min"] == shot["min"] and norm(g["scorer"]) == norm(shot["player"]):
            return g.get("assist")
    return None


def build_goal_sequences(D):
    """Port of match.js buildGoalSequences: rebuild each goal's build-up."""
    ev = []
    for p in D.get("passes") or []:
        if p.get("ok"):
            ev.append({"k": "pass", "t": agmT(p), "team": p["team"], "x": p["x"], "y": p["y"],
                       "ex": p["ex"], "ey": p["ey"], "player": p["player"], "cross": bool(p.get("cross"))})
    for d in D.get("dribbles") or []:
        if d.get("ok"):
            ev.append({"k": "dribble", "t": agmT(d), "team": d["team"], "x": d["x"], "y": d["y"],
                       "player": d["player"]})
    ev.sort(key=lambda e: e["t"])
    saves = D.get("saves") or []
    shots = D.get("shots") or []

    seqs = []
    for shot in [s for s in shots if s.get("goal")]:
        T = agmT(shot)
        chain = [e for e in ev if e["team"] == shot["team"] and T - 35 <= e["t"] <= T]
        seq = []
        for i in range(len(chain) - 1, -1, -1):
            if seq and seq[0]["t"] - chain[i]["t"] > 6:
                break
            seq.insert(0, chain[i])
        # rebound: a same-team shot saved/blocked in the ~4s before the goal
        prior, best = None, -1
        for s2 in shots:
            tt = agmT(s2)
            if s2["team"] == shot["team"] and not s2.get("goal") and tt < T and T - tt <= 4 and tt > best:
                best, prior = tt, s2
        rebound = False
        if prior:
            rebound = True
            seq.append({"k": "shot_eff", "team": prior["team"], "x": prior["x"], "y": prior["y"],
                        "player": prior["player"], "xg": prior.get("xg")})
            sv, sb = None, -1
            for v in saves:
                tt = agmT(v)
                if v["team"] != shot["team"] and abs(tt - T) <= 2 and tt > sb:
                    sb, sv = tt, v
            if sv:
                seq.append({"k": "save", "team": sv["team"], "x": sv["x"], "y": sv["y"], "player": sv["player"]})
        seq.append({"k": "shot", "team": shot["team"], "x": shot["x"], "y": shot["y"],
                    "player": shot["player"], "xg": shot.get("xg")})
        seqs.append(_finalize_seq(seq, D, scorer=shot["player"], mn=shot["min"],
                                  side=shot["team"], assist=assist_for(D, shot), xg=shot.get("xg")))

    # own goals: reconstruct the beneficiary's build-up
    for g in D.get("goals") or []:
        if not g.get("own") or g.get("x") is None:
            continue
        benef = g["team"]
        og_end = ((g.get("min") or 0) + 1) * 60
        T = (g.get("min") or 0) * 60 + 59
        for e in reversed(ev):
            if e["team"] == benef and e["t"] <= og_end:
                T = e["t"]
                break
        chain = [e for e in ev if e["team"] == benef and T - 30 <= e["t"] <= T]
        seq = []
        for i in range(len(chain) - 1, -1, -1):
            if seq and seq[0]["t"] - chain[i]["t"] > 6:
                break
            seq.insert(0, chain[i])
        seq.append({"k": "shot", "team": benef, "x": g["x"], "y": g["y"], "player": g["scorer"], "og": True})
        seqs.append(_finalize_seq(seq, D, scorer="Own goal", mn=g["min"], side=benef,
                                  assist=None, xg=None, own=True, og_by=g["scorer"]))

    seqs.sort(key=lambda s: s.get("min") or 0)
    return seqs


def _finalize_seq(seq, D, scorer, mn, side, assist, xg, own=False, og_by=None):
    nm = num_map(D)
    steps = []
    for st in seq:
        out = {"k": st["k"], "x": round(st["x"], 1), "y": round(st["y"], 1), "player": st.get("player")}
        if st.get("ex") is not None:
            out["ex"], out["ey"] = round(st["ex"], 1), round(st["ey"], 1)
        if st.get("cross"):
            out["cross"] = True
        if st.get("xg") is not None:
            out["xg"] = round(st["xg"], 3)
        if st["k"] == "save":                 # save recorded in the opposition frame
            out["team"] = st["team"]
        if st.get("og"):
            out["og"] = True
        n = nm.get(norm(st.get("player")))
        if n is not None:
            out["num"] = n
        steps.append(out)
    ppl = {norm(s["player"]) for s in seq if s["k"] != "save" and s.get("player") and not s.get("og")}
    res = {
        "scorer": scorer, "min": mn, "side": side, "assist": assist,
        "xg": round(xg, 3) if xg is not None else None,
        "players": len(ppl),
        "passes": sum(1 for s in seq if s["k"] == "pass"),
        "steps": steps,
    }
    if own:
        res["own"] = True
        res["ogBy"] = og_by
    return res


def team_agg(D, side):
    """Event-stream aggregates that don't rely on FotMob match_stats."""
    passes = [p for p in (D.get("passes") or []) if p["team"] == side]
    ok = [p for p in passes if p.get("ok")]
    drib = [d for d in (D.get("dribbles") or []) if d["team"] == side and d.get("ok")]
    saves = [v for v in (D.get("saves") or []) if v["team"] == side]
    shots = [s for s in (D.get("shots") or []) if s["team"] == side]
    return {
        "passes_ok": len(ok),
        "pass_acc": round(100 * len(ok) / len(passes)) if passes else 0,
        "dribbles": len(drib),
        "saves": len(saves),
        "shots": len(shots),
        "sot": sum(1 for s in shots if s.get("onTarget")),
        "big": sum(1 for s in shots if s.get("big")),
        "xg_sum": round(sum(s.get("xg") or 0 for s in shots), 2),
    }


def build_stats(D, ms, hA, aA):
    """Head-to-head stat panel. Prefer FotMob match_stats; fall back to the
    event stream so WhoScored-only matches still get a full panel."""
    def pick(key, fb_h, fb_a):
        h = ms.get(key + "_home") if ms else None
        a = ms.get(key + "_away") if ms else None
        return (h if h is not None else fb_h, a if a is not None else fb_a)

    stats = []
    poss_h = ms.get("possession_home") if ms else None
    poss_a = ms.get("possession_away") if ms else None
    if poss_h is not None and poss_a is not None:
        stats.append({"label": "Possession", "h": poss_h, "a": poss_a, "fmt": "pct"})

    xg_h = ms.get("xg_home") if ms else None
    xg_a = ms.get("xg_away") if ms else None
    if xg_h is None or xg_a is None:
        xg_h, xg_a = hA["xg_sum"], aA["xg_sum"]
    stats.append({"label": "Expected goals (xG)", "h": xg_h, "a": xg_a, "fmt": "dec"})

    sh_h, sh_a = pick("shots", hA["shots"], aA["shots"])
    stats.append({"label": "Shots", "h": sh_h, "a": sh_a})
    sot_h, sot_a = pick("shots_on_target", hA["sot"], aA["sot"])
    stats.append({"label": "Shots on target", "h": sot_h, "a": sot_a})
    bc_h, bc_a = pick("big_chances_created", hA["big"], aA["big"])
    stats.append({"label": "Big chances", "h": bc_h, "a": bc_a})
    stats.append({"label": "Passes completed", "h": hA["passes_ok"], "a": aA["passes_ok"]})
    stats.append({"label": "Pass accuracy", "h": hA["pass_acc"], "a": aA["pass_acc"], "fmt": "pct"})
    stats.append({"label": "Dribbles won", "h": hA["dribbles"], "a": aA["dribbles"]})
    stats.append({"label": "Keeper saves", "h": hA["saves"], "a": aA["saves"]})
    return stats, [xg_h, xg_a]


def build_match(detail_path, raw_dir):
    D = load_detail(detail_path)
    mid = D["id"]
    raw_path = os.path.join(raw_dir, mid + ".json")
    ms = None
    if os.path.exists(raw_path):
        ms = json.load(open(raw_path)).get("match_stats") or None

    hA, aA = team_agg(D, "home"), team_agg(D, "away")
    stats, xg = build_stats(D, ms, hA, aA)

    shots = [{
        "team": s["team"], "x": s["x"], "y": s["y"], "min": s["min"], "player": s["player"],
        "xg": round(s.get("xg") or 0, 3), "goal": bool(s.get("goal")),
        "onTarget": bool(s.get("onTarget")), "blocked": bool(s.get("blocked")),
        "body": s.get("body") or "", "sit": s.get("sit") or "",
    } for s in (D.get("shots") or [])]

    goals = [{
        "team": g["team"], "min": g["min"], "scorer": g["scorer"], "assist": g.get("assist"),
        "pen": bool(g.get("pen")), "own": bool(g.get("own")),
    } for g in (D.get("goals") or [])]

    return {
        "id": mid,
        "home": {"name": D["home"]["name"], "score": D["home"]["score"], "color": D["home"].get("color") or "#888"},
        "away": {"name": D["away"]["name"], "score": D["away"]["score"], "color": D["away"].get("color") or "#888"},
        "date": D.get("date"), "venue": D.get("venue") or "", "stage": D.get("stage") or "",
        "xg": [round(xg[0], 2) if xg[0] is not None else 0, round(xg[1], 2) if xg[1] is not None else 0],
        "goals": goals, "stats": stats, "shots": shots,
        "replays": build_goal_sequences(D),
    }


def generate(source, out_dir):
    """Rebuild every Argentina match JSON + index.json. Returns the match count."""
    detail_dir = os.path.join(source, "wc2026_dashboard", "matches_detail")
    raw_dir = os.path.join(source, "wc2026", "matches")
    os.makedirs(out_dir, exist_ok=True)

    matches = []
    for path in sorted(glob.glob(os.path.join(detail_dir, "*.js"))):
        try:
            D = load_detail(path)
        except Exception:
            continue
        if TEAM not in (D["home"]["name"], D["away"]["name"]):
            continue
        M = build_match(path, raw_dir)
        out_path = os.path.join(out_dir, M["id"] + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(M, f, ensure_ascii=False, separators=(",", ":"))
        arg = "home" if M["home"]["name"] == TEAM else "away"
        opp = M["away"] if arg == "home" else M["home"]
        matches.append({
            "id": M["id"],
            "file": "assets/data/argentina/" + M["id"] + ".json",
            "date": M["date"], "stage": M["stage"],
            "home": {"name": M["home"]["name"], "score": M["home"]["score"]},
            "away": {"name": M["away"]["name"], "score": M["away"]["score"]},
            "opponent": opp["name"],
            "argSide": arg,
        })
        print("wrote", os.path.basename(out_path), "-", M["home"]["name"], M["home"]["score"],
              "-", M["away"]["score"], M["away"]["name"], "(%d goal replays)" % len(M["replays"]))

    matches.sort(key=lambda m: m["date"])
    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"team": TEAM, "matches": matches}, f, ensure_ascii=False, indent=1)
    print("wrote index.json -", len(matches), "Argentina matches")
    return len(matches)


def main():
    ap = argparse.ArgumentParser(description="Generate the Argentina Match Centre data.")
    ap.add_argument("--source", help="XWORLDCUPTWIT repo root (else WC_SOURCE env or sibling checkout)")
    ap.add_argument("--out", help="output dir for the argentina/*.json files (default: <here>/argentina)")
    args = ap.parse_args()
    source = resolve_source(args.source)
    out_dir = args.out or os.environ.get("WC_OUT") or os.path.join(HERE, "argentina")
    generate(source, out_dir)


if __name__ == "__main__":
    main()
