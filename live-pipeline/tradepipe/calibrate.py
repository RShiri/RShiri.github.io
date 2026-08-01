#!/usr/bin/env python3
"""Fit team attack/defence rates from ALL of Ram's scraped football data
(EPL + La Liga + three World Cups, ~3,275 matches) and back-test the
in-play model, mini-TRADE360 style.

The fit is a Dixon-Coles-lite with empirical-Bayes shrinkage, one baseline
per COMPETITION (an EPL goal habitat is not a World Cup goal habitat):

    mu_c  = competition baseline = weighted mean single-team 90-min xG
    att_T = (sum w_i * xG for  T + k*mu_c) / (sum w_i + k)   [per-match rate]
    def_T = (sum w_i * xG against T + k*mu_c) / (sum w_i + k)
    lam_home = att_H * def_A / mu_c * hfa      [hfa = 1 on neutral venues]
    lam_away = att_A * def_H / mu_c / hfa

Weights w_i are a recency decay (DECAY ** seasons_ago, WC editions age in
4-year steps) so 2025-26 form dominates a club's rate. Home advantage hfa
is fit as sqrt(mean home xG / mean away xG) over league matches only —
World Cup venues are neutral. Shrinkage strength k is tuned over
{1, 2, 4, 8, 16} by holdout Brier.

Honest evaluation: train on league seasons 2022-23..2024-25 + WC2018 +
WC2022, evaluate the Brier score at minutes 0/15/.../90 on the held-out
2025-26 league seasons + WC2026, against two baselines: the same model
with w = 0 (no momentum) and a constant global base-rate triple. The
production params are then refit on ALL data.

Run from anywhere:
    python3 live-pipeline/tradepipe/calibrate.py
Writes assets/data/winprob/model_params.json (v2) and, when the scraper
clones are present, a winprob_params.js into each dashboard.

With no scraper clones at all it falls back to the 8 argentina match
JSONs (competition "WC" only) so the pipeline demo keeps working.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent                           # rshiri.github.io/

# Load the sibling modules directly by file path so this script stays
# standalone (no tradepipe package import, no __init__ side effects).
def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

model = _load("winprob_model", "model.py")
corpus = _load("winprob_corpus", "corpus.py")

K_GRID = [1, 2, 4, 8, 16]   # shrinkage strengths tried (pseudo-matches at mu)
W = 0.35                    # momentum weight used by the live model
DECAY = 0.8                 # recency: weight = DECAY ** seasons_ago
CHECKPOINTS = [0, 15, 30, 45, 60, 75, 90]
HOLDOUT = {"EPL": "2025-26", "LaLiga": "2025-26", "WC": "2026"}


# ------------------------------------------------------------------ fitting

def season_age(competition, season, latest):
    """Whole seasons between `season` and the latest one in the fit set.
    Leagues age one step per season ("2024-25" is 1 behind "2025-26");
    World Cup editions age one step per 4-year cycle."""
    if competition == "WC":
        return (int(latest) - int(season)) // 4
    return int(latest[:4]) - int(season[:4])


def fit(matches, k, decay=DECAY):
    """Fit {mu per competition, namespaced team rates, hfa} from matches.

    Returns {"mu": {comp: mu_c}, "teams": {"EPL/Arsenal": {...}, ...},
    "hfa": float, "k": k, "decay": decay}. Team keys are namespaced by
    competition so "WC/France" and a hypothetical "EPL/France" never mix."""
    latest = {}                              # comp -> latest season seen
    for M in matches:
        c = M["competition"]
        if c not in latest or M["season"] > latest[c]:
            latest[c] = M["season"]

    comp_wsum = {}                           # comp -> [w*xg sum, w sum]
    totals = {}                              # key -> [w*for, w*against, w, n]
    hfa_home = hfa_away = hfa_n = 0
    for M in matches:
        c = M["competition"]
        w = decay ** season_age(c, M["season"], latest[c])
        xg_h, xg_a = M["xg"]
        cw = comp_wsum.setdefault(c, [0.0, 0.0])
        for name, xf, xa in ((M["home"], xg_h, xg_a),
                             (M["away"], xg_a, xg_h)):
            row = totals.setdefault(c + "/" + name, [0.0, 0.0, 0.0, 0])
            row[0] += w * xf
            row[1] += w * xa
            row[2] += w
            row[3] += 1
            cw[0] += w * xf
            cw[1] += w
        if not M["is_neutral"]:              # league matches drive hfa
            hfa_home += xg_h
            hfa_away += xg_a
            hfa_n += 1

    mu = {c: s / n for c, (s, n) in comp_wsum.items()}
    teams = {}
    for key, (wxf, wxa, wn, n) in sorted(totals.items()):
        mu_c = mu[key.split("/", 1)[0]]
        teams[key] = {
            "att": (wxf + k * mu_c) / (wn + k),
            "def": (wxa + k * mu_c) / (wn + k),
            "matches": n,
        }
    hfa = math.sqrt(hfa_home / hfa_away) if hfa_n else 1.0
    return {"mu": mu, "teams": teams, "hfa": hfa, "k": k, "decay": decay}


def rates(teams, mu, key):
    """(att, def) for a namespaced team key; unseen teams (fallback mode
    placeholders, first-time WC qualifiers) get the competition baseline."""
    t = teams.get(key)
    if t is None:
        return mu, mu
    return t["att"], t["def"]


def prematch_lams(teams, mu, home_key, away_key, hfa=1.0):
    """Pre-match expected goals per side: lam = att * opp_def / mu, with
    the multiplicative home-field boost hfa (pass 1.0 for neutral venues:
    every World Cup match). mu is the competition baseline the keys live
    in; keys are namespaced ("EPL/Arsenal")."""
    att_h, def_h = rates(teams, mu, home_key)
    att_a, def_a = rates(teams, mu, away_key)
    return att_h * def_a / mu * hfa, att_a * def_h / mu / hfa


def match_lams(F, M):
    """Pre-match lams for a normalized corpus match under fit F."""
    c = M["competition"]
    mu_c = F["mu"].get(c) or sum(F["mu"].values()) / len(F["mu"])
    hfa = 1.0 if M["is_neutral"] else F["hfa"]
    return prematch_lams(F["teams"], mu_c, c + "/" + M["home"],
                         c + "/" + M["away"], hfa)


# --------------------------------------------------------------- evaluation

def score_at(M, t):
    """(home, away) score counting goals up to and including minute t on
    the 90-minute market clock (model.effective_min: stoppage goals fold
    into minute 90, extra-time goals in WC knockouts don't count)."""
    h = a = 0
    for g in M["goals"]:
        m = model.effective_min(g["min"], M["has_extra_time"])
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
        m = model.effective_min(s["min"], M["has_extra_time"])
        if s["team"] == side and m is not None and t - 15 < m <= t:
            total += s["xg"]
    return total


def outcome_90(M):
    """One-hot (H, D, A) of the 90-minute result. Stoppage-time goals count
    (they settle real 1X2 markets); extra-time goals do not: the model
    prices the 90-minute market."""
    h, a = score_at(M, 90)
    if h > a:
        return (1.0, 0.0, 0.0)
    if h == a:
        return (0.0, 1.0, 0.0)
    return (0.0, 0.0, 1.0)


def base_rates(matches):
    """Global (pH, pD, pA) frequency of 90-minute outcomes — the
    "always quote 0.44/0.27/0.29" constant baseline."""
    counts = [0, 0, 0]
    for M in matches:
        o = outcome_90(M)
        counts[o.index(1.0)] += 1
    n = float(len(matches))
    return tuple(c / n for c in counts)


def evaluate(matches, F, w, constant=None):
    """Mean Brier per checkpoint minute, overall and per competition.

    constant=(pH,pD,pA) scores that fixed triple instead of the model —
    the same number at every checkpoint, it never looks at the pitch."""
    sums = {t: 0.0 for t in CHECKPOINTS}
    comp_sums = {}                           # comp -> {t: sum}, comp -> n
    comp_n = {}
    for M in matches:
        c = M["competition"]
        cs = comp_sums.setdefault(c, {t: 0.0 for t in CHECKPOINTS})
        comp_n[c] = comp_n.get(c, 0) + 1
        target = outcome_90(M)
        if constant is None:
            lam_h, lam_a = match_lams(F, M)
            live = model.InPlayModel(lam_h, lam_a, w=w)
        for t in CHECKPOINTS:
            if constant is None:
                h, a = score_at(M, t)
                p = live.probs(t, h, a, xg_recent15(M, "home", t),
                               xg_recent15(M, "away", t))
                probs = (p["pH"], p["pD"], p["pA"])
            else:
                probs = constant
            b = sum((pi - oi) ** 2 for pi, oi in zip(probs, target))
            sums[t] += b
            cs[t] += b
    n = len(matches)
    overall = {t: sums[t] / n for t in CHECKPOINTS}
    per_comp = {c: {t: comp_sums[c][t] / comp_n[c] for t in CHECKPOINTS}
                for c in comp_sums}
    return overall, per_comp, comp_n


def split_holdout(matches):
    """(train, eval) split: the newest league season + WC2026 held out."""
    train, held = [], []
    for M in matches:
        (held if M["season"] == HOLDOUT.get(M["competition"]) else train).append(M)
    return train, held


# ------------------------------------------------------------ data loading

def load_argentina(data_dir):
    """Fallback corpus: the 8 argentina match JSONs, normalized to the
    corpus shape (competition "WC"; clean stage labels pick out the
    knockouts, and corpus.knockout_played_extra_time decides — from the
    event stream, these files have no maxMin — whether a knockout
    actually played extra time)."""
    idx = json.load(open(data_dir / "index.json", encoding="utf-8"))
    matches = []
    for m in idx["matches"]:
        raw = json.load(open(data_dir / (m["id"] + ".json"), encoding="utf-8"))
        stage = raw.get("stage") or ""
        matches.append({
            "competition": "WC",
            "season": "2026",
            "stage": stage,
            "date": raw.get("date") or "",
            "home": raw["home"]["name"],
            "away": raw["away"]["name"],
            "shots": raw.get("shots") or [],
            "goals": raw.get("goals") or [],
            "has_extra_time": (not corpus.is_groupish(stage)
                               and corpus.knockout_played_extra_time(raw)),
            "is_neutral": True,
            "xg": list(raw["xg"]),
        })
    return matches


# ----------------------------------------------------------------- outputs

def corpus_summary(matches):
    """Per-competition "EPL: 1520 matches, 40590 shots" description list."""
    agg = {}
    for M in matches:
        row = agg.setdefault(M["competition"], [0, 0])
        row[0] += 1
        row[1] += len(M["shots"])
    return ["%s: %d matches, %d shots" % (c, n, s)
            for c, (n, s) in sorted(agg.items())]


def write_params(out_path, F, brier_block, generated_from):
    params = {
        "version": 2,
        "mu": {c: round(v, 4) for c, v in sorted(F["mu"].items())},
        "hfa": round(F["hfa"], 4),
        "k": F["k"],
        "w": W,
        "decay": F["decay"],
        "teams": {key: {"att": round(t["att"], 4), "def": round(t["def"], 4),
                        "matches": t["matches"]}
                  for key, t in F["teams"].items()},
        "brier": brier_block,
        "generated_from": generated_from,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(params, f, ensure_ascii=False, indent=1)
    print("wrote %s (%.1f KB)" % (out_path, out_path.stat().st_size / 1024))


def write_dashboard_params(roots, F):
    """One winprob_params.js per scraper dashboard, with that competition's
    teams only (names WITHOUT the namespace prefix). The WC dashboard gets
    hfa 1.0 and a neutral flag — every World Cup venue is neutral."""
    targets = {
        "EPL": ("epl_dashboard", roots.get("EPL")),
        "LaLiga": ("laliga_dashboard", roots.get("LaLiga")),
        "WC": ("wc2026_dashboard", roots.get("WC")),
    }
    for comp, (dash, root) in targets.items():
        if root is None or comp not in F["mu"]:
            continue
        neutral = comp == "WC"
        teams = {key.split("/", 1)[1]: {"att": round(t["att"], 4),
                                        "def": round(t["def"], 4)}
                 for key, t in F["teams"].items()
                 if key.startswith(comp + "/")}
        payload = {
            "version": 2,
            "competition": comp,
            "mu": round(F["mu"][comp], 4),
            "hfa": 1.0 if neutral else round(F["hfa"], 4),
            "neutral": neutral,
            "w": W,
            "maxGoals": model.MAX_GOALS,
            "lamFloor": model.LAM_FLOOR,
            "teams": teams,
        }
        out = Path(root) / dash / "winprob_params.js"
        text = ("// generated by rshiri.github.io/live-pipeline/tradepipe/"
                "calibrate.py - do not edit by hand\n"
                "window.WINPROB_PARAMS = %s;\n"
                % json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        out.write_text(text, encoding="utf-8")
        print("wrote %s (%.1f KB, %d teams)" % (out, out.stat().st_size / 1024,
                                                len(teams)))


# -------------------------------------------------------------------- main

def print_brier_table(title, cps, rows, n_eval):
    print(title + " (n=%d matches)" % n_eval)
    print("  min  " + "".join("%12s" % name for name, _ in rows))
    for t in cps:
        print("  %3d  " % t + "".join("%12.4f" % vals[t] for _, vals in rows))


def main():
    ap = argparse.ArgumentParser(
        description="Fit win-prob model params from all scraped corpora.")
    ap.add_argument("--epl", help="XEPL repo root (default: sibling clone or /workspace/xepl)")
    ap.add_argument("--laliga", help="XLALIGA repo root (default: sibling clone or /workspace/xlaliga)")
    ap.add_argument("--wc", help="XWORLDCUPTWIT repo root (default: sibling clone or /workspace/xworldcuptwit)")
    ap.add_argument("--data", default=str(REPO / "assets" / "data" / "argentina"),
                    help="fallback argentina match dir when no corpora found")
    ap.add_argument("--out", default=str(REPO / "assets" / "data" / "winprob" / "model_params.json"),
                    help="output params file (default: assets/data/winprob/model_params.json)")
    ap.add_argument("--no-dashboards", action="store_true",
                    help="skip writing winprob_params.js into the scraper clones")
    args = ap.parse_args()

    corpora, roots = corpus.default_corpora(args.epl, args.laliga, args.wc,
                                            repo_root=REPO)
    if corpora:
        matches = list(corpus.iter_matches(corpora))
        run_full(args, matches, roots)
    else:
        print("WARNING: no scraper corpora found (../XEPL, ../XLALIGA, "
              "../XWORLDCUPTWIT, /workspace equivalents, or the vendored "
              "projects/ copies).")
        print("WARNING: falling back to the 8 argentina match JSONs -- "
              "params will cover competition 'WC' only and the Brier "
              "numbers are an in-sample smoke test, not a benchmark.")
        matches = load_argentina(Path(args.data))
        run_fallback(args, matches)


def run_full(args, matches, roots):
    n_shots = sum(len(M["shots"]) for M in matches)
    print("total: %d matches, %d shots" % (len(matches), n_shots))
    print()

    # ---- honest evaluation: temporal holdout ----
    train, held = split_holdout(matches)
    print("holdout: train %d matches (2022-23..2024-25 leagues + WC2018 + "
          "WC2022), eval %d (2025-26 leagues + WC2026)" % (len(train), len(held)))

    best_k, best_score, best_brier = None, None, None
    for k in K_GRID:
        Fk = fit(train, k)
        overall, _, _ = evaluate(held, Fk, w=W)
        score = sum(overall.values()) / len(overall)
        print("  k=%-2d  mean holdout Brier %.5f" % (k, score))
        if best_score is None or score < best_score:
            best_k, best_score = k, score
    print("chosen k = %d (lowest mean holdout Brier)" % best_k)
    print()

    F_train = fit(train, best_k)
    const = base_rates(train)
    b_model, b_model_pc, comp_n = evaluate(held, F_train, w=W)
    b_w0, b_w0_pc, _ = evaluate(held, F_train, w=0.0)
    b_const, b_const_pc, _ = evaluate(held, F_train, w=W, constant=const)

    print("constant baseline (train outcome rates): H %.3f / D %.3f / A %.3f"
          % const)
    print_brier_table("mean Brier vs 90-min outcome, temporal holdout",
                      CHECKPOINTS,
                      [("model w=%.2f" % W, b_model), ("w=0", b_w0),
                       ("constant", b_const)], len(held))
    for c in sorted(comp_n):
        print_brier_table("  -- %s holdout" % c, CHECKPOINTS,
                          [("model", b_model_pc[c]), ("w=0", b_w0_pc[c]),
                           ("constant", b_const_pc[c])], comp_n[c])
    print()

    # ---- production fit: everything, best k ----
    F = fit(matches, best_k)
    print("production fit on all %d matches:" % len(matches))
    print("  mu  " + "  ".join("%s %.4f" % (c, F["mu"][c])
                               for c in sorted(F["mu"])))
    print("  hfa %.4f   k %d   decay %.2f   teams %d"
          % (F["hfa"], F["k"], F["decay"], len(F["teams"])))

    brier_block = {
        "design": "temporal holdout: train on league seasons 2022-23..2024-25 "
                  "+ WC2018 + WC2022, evaluate on 2025-26 leagues + WC2026; "
                  "production rates refit on all data with the chosen k",
        "checkpoints": CHECKPOINTS,
        "model": [round(b_model[t], 4) for t in CHECKPOINTS],
        "baseline_w0": [round(b_w0[t], 4) for t in CHECKPOINTS],
        "constant": [round(b_const[t], 4) for t in CHECKPOINTS],
        "constant_probs": [round(p, 4) for p in const],
        "n_eval": len(held),
        "per_competition": {
            c: {"model": [round(b_model_pc[c][t], 4) for t in CHECKPOINTS],
                "baseline_w0": [round(b_w0_pc[c][t], 4) for t in CHECKPOINTS],
                "constant": [round(b_const_pc[c][t], 4) for t in CHECKPOINTS],
                "n": comp_n[c]}
            for c in sorted(comp_n)},
    }
    generated_from = corpus_summary(matches)
    write_params(Path(args.out), F, brier_block, generated_from)
    if not args.no_dashboards:
        write_dashboard_params(roots, F)


def run_fallback(args, matches):
    F = fit(matches, k=1)
    b_model, _, _ = evaluate(matches, F, w=W)
    b_w0, _, _ = evaluate(matches, F, w=0.0)

    print("fitted %d teams from %d matches, mu_WC = %.4f xG per team-match"
          % (len(F["teams"]), len(matches), F["mu"]["WC"]))
    print_brier_table("mean in-sample Brier (smoke test only)", CHECKPOINTS,
                      [("model w=%.2f" % W, b_model), ("w=0", b_w0)],
                      len(matches))

    brier_block = {
        "design": "in-sample on the 8 argentina matches (fallback mode; "
                  "no holdout possible)",
        "checkpoints": CHECKPOINTS,
        "model": [round(b_model[t], 4) for t in CHECKPOINTS],
        "baseline_w0": [round(b_w0[t], 4) for t in CHECKPOINTS],
        "n_eval": len(matches),
    }
    write_params(Path(args.out), F, brier_block,
                 ["fallback: assets/data/argentina (8 matches)"])


if __name__ == "__main__":
    main()
