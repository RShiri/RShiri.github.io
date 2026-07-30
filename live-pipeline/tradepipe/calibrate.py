#!/usr/bin/env python3
"""Fit team attack/defence rates from the Argentina WC2026 match JSONs and
back-test the in-play model, mini-TRADE360 style.

The fit is a Dixon-Coles-lite with empirical-Bayes shrinkage (k = 1):

    mu    = tournament baseline = mean single-team xG per match
    att_T = (total xG for  T + k*mu) / (n_T + k)     [per-match rate]
    def_T = (total xG against T + k*mu) / (n_T + k)
    lam(A vs B) = att_A * def_B / mu                 [no home advantage:
                                                      neutral WC venues]

Teams never seen in the data (knockout placeholders) fall back to
att = def = mu. Evaluation: Brier score of the in-play model at minutes
0/15/.../90 against the actual 90-minute outcome, vs a w = 0 baseline
(pre-match rates only, no momentum). n = 8 matches, so treat the numbers
as a smoke test, not a benchmark.

Run from anywhere:
    python3 live-pipeline/tradepipe/calibrate.py
Writes assets/data/winprob/model_params.json.
"""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent                           # rshiri.github.io/

# Load the sibling model.py directly by file path so this script stays
# standalone (no tradepipe package import, no __init__ side effects).
_spec = importlib.util.spec_from_file_location("winprob_model", HERE / "model.py")
model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model)

K = 1                       # shrinkage strength (pseudo-matches at rate mu)
W = 0.35                    # momentum weight used by the live model
CHECKPOINTS = [0, 15, 30, 45, 60, 75, 90]


def load_matches(data_dir):
    idx = json.load(open(data_dir / "index.json", encoding="utf-8"))
    matches = []
    for m in idx["matches"]:
        matches.append(json.load(open(data_dir / (m["id"] + ".json"), encoding="utf-8")))
    return matches


def fit_teams(matches, k=K):
    """Per-team totals -> shrunk per-match attack/defence rates + baseline mu."""
    totals = {}                                     # name -> [xg_for, xg_against, n]
    team_match_xg = []                              # every single-team xG figure
    for M in matches:
        names = (M["home"]["name"], M["away"]["name"])
        xg = M["xg"]                                # [homeTotal, awayTotal]
        for side, name in enumerate(names):
            row = totals.setdefault(name, [0.0, 0.0, 0])
            row[0] += xg[side]
            row[1] += xg[1 - side]
            row[2] += 1
            team_match_xg.append(xg[side])

    mu = sum(team_match_xg) / len(team_match_xg)
    teams = {}
    for name, (xg_for, xg_against, n) in sorted(totals.items()):
        teams[name] = {
            "att": (xg_for + k * mu) / (n + k),
            "def": (xg_against + k * mu) / (n + k),
            "matches": n,
        }
    return mu, teams


def rates(teams, mu, name):
    """(att, def) for a team; unseen names (placeholders) get the baseline."""
    t = teams.get(name)
    if t is None:
        return mu, mu
    return t["att"], t["def"]


def prematch_lams(teams, mu, home_name, away_name):
    """Pre-match expected goals for each side: lam_A = att_A * def_B / mu."""
    att_h, def_h = rates(teams, mu, home_name)
    att_a, def_a = rates(teams, mu, away_name)
    return att_h * def_a / mu, att_a * def_h / mu


def score_at(M, t):
    """(home, away) score counting goals up to and including minute t on the
    90-minute market clock (model.effective_min: group-stage stoppage goals
    fold into minute 90, extra-time goals don't count)."""
    h = a = 0
    for g in M["goals"]:
        m = model.effective_min(g["min"], M.get("stage", ""))
        if m is not None and m <= t:
            if g["team"] == "home":
                h += 1
            else:
                a += 1
    return h, a


def xg_recent15(M, side, t):
    """xG a side generated in the (t-15, t] window, from the shot stream."""
    total = 0.0
    for s in M["shots"]:
        m = model.effective_min(s["min"], M.get("stage", ""))
        if s["team"] == side and m is not None and t - 15 < m <= t:
            total += s["xg"]
    return total


def outcome_90(M):
    """One-hot (H, D, A) of the 90-minute result. Stoppage-time goals count
    (they settle real 1X2 markets); extra-time goals (e.g. the Final's 105'
    winner) do not: the model prices the 90-minute market."""
    h, a = score_at(M, 90)
    if h > a:
        return (1.0, 0.0, 0.0)
    if h == a:
        return (0.0, 1.0, 0.0)
    return (0.0, 0.0, 1.0)


def evaluate(matches, teams, mu, w):
    """Mean Brier score per checkpoint minute for momentum weight w."""
    sums = {t: 0.0 for t in CHECKPOINTS}
    for M in matches:
        lam_h, lam_a = prematch_lams(teams, mu, M["home"]["name"], M["away"]["name"])
        live = model.InPlayModel(lam_h, lam_a, w=w)
        target = outcome_90(M)
        for t in CHECKPOINTS:
            h, a = score_at(M, t)
            p = live.probs(t, h, a, xg_recent15(M, "home", t), xg_recent15(M, "away", t))
            probs = (p["pH"], p["pD"], p["pA"])
            sums[t] += sum((pi - oi) ** 2 for pi, oi in zip(probs, target))
    n = len(matches)
    return {t: sums[t] / n for t in CHECKPOINTS}


def main():
    ap = argparse.ArgumentParser(description="Fit win-prob model params from the Argentina match data.")
    ap.add_argument("--data", default=str(REPO / "assets" / "data" / "argentina"),
                    help="match JSON dir (default: assets/data/argentina)")
    ap.add_argument("--out", default=str(REPO / "assets" / "data" / "winprob" / "model_params.json"),
                    help="output params file (default: assets/data/winprob/model_params.json)")
    args = ap.parse_args()

    data_dir = Path(args.data)
    matches = load_matches(data_dir)
    mu, teams = fit_teams(matches)

    brier_model = evaluate(matches, teams, mu, w=W)
    brier_base = evaluate(matches, teams, mu, w=0.0)

    print("fitted %d teams from %d matches, mu = %.4f xG per team-match" % (len(teams), len(matches), mu))
    for name, t in teams.items():
        print("  %-12s att %.3f  def %.3f  (n=%d)" % (name, t["att"], t["def"], t["matches"]))
    print()
    print("mean Brier vs 90-min outcome (n=%d matches -- tiny sample, smoke test only)" % len(matches))
    print("  min   model w=%.2f   baseline w=0" % W)
    for t in CHECKPOINTS:
        print("  %3d      %.4f         %.4f" % (t, brier_model[t], brier_base[t]))

    params = {
        "mu": round(mu, 6),
        "k": K,
        "w": W,
        "teams": {name: {"att": round(t["att"], 6), "def": round(t["def"], 6),
                         "matches": t["matches"]} for name, t in teams.items()},
        "brier": {
            "checkpoints": CHECKPOINTS,
            "model": [round(brier_model[t], 6) for t in CHECKPOINTS],
            "baseline_w0": [round(brier_base[t], 6) for t in CHECKPOINTS],
            "n_matches": len(matches),
            "note": "mean Brier per checkpoint minute vs the 90-min outcome; "
                    "n=8 matches so indicative only",
        },
        "generated_from": "assets/data/argentina",
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(params, f, ensure_ascii=False, indent=1)
    print()
    print("wrote", out_path)


if __name__ == "__main__":
    main()
