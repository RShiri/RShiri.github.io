#!/usr/bin/env python3
"""Fit the in-play win-probability model from ALL of Ram's scraped football
data (EPL + La Liga + three World Cups, ~3,272 matches) and back-test it,
mini-TRADE360 style.

TEAM RATINGS are a Dixon-Coles-lite fit with empirical-Bayes shrinkage, one
baseline per COMPETITION (an EPL goal habitat is not a World Cup one):

    mu_c  = competition baseline = weighted mean single-team 90-min xG
    att_T = (sum w_i * xG for  T + k*mu_c) / (sum w_i + k)   [per-match rate]
    def_T = (sum w_i * xG against T + k*mu_c) / (sum w_i + k)
    lam_home = att_H * def_A / mu_c * hfa      [hfa = 1 on neutral venues]
    lam_away = att_A * def_H / mu_c / hfa

Weights w_i are a recency decay (decay ** seasons_ago, WC editions age in
4-year steps). Home advantage hfa is fit as sqrt(mean home xG / mean away
xG) over league matches only — World Cup venues are neutral.

MODEL SHAPE (the in-play part) is tuned rather than assumed: the momentum
weight w and its window, the empirical remaining-scoring profile, the
score-state multipliers, the Dixon-Coles rho, and the rating hypers k and
decay. Red-card multipliers are not tuned by score at all — they are
measured directly from post-dismissal xG (fit_red_effect).

THE PROTOCOL matters more than any of it. Three disjoint blocks in time:

    inner   league 2022-23, 2023-24 + WC2018      fit ratings while tuning
    val     league 2024-25      + WC2022          choose every hyper
    holdout league 2025-26      + WC2026          scored ONCE, at the end

Every hyper is chosen on `val`; the holdout is touched exactly once, by the
single finished configuration, and reported against two baselines (the same
model with w = 0, and a constant base-rate triple). v2 of this script tuned
k on the holdout it then reported, which flatters the number — the split
above is the fix. Production rates are refit on ALL data with the chosen
hypers once the reporting is done.

Run from anywhere:
    python3 live-pipeline/tradepipe/calibrate.py
Writes assets/data/winprob/model_params.json (v3) and, when the corpora are
present, a winprob_params.js into each dashboard.

With no corpora at all it falls back to the 8 argentina match JSONs
(competition "WC" only) so the pipeline demo keeps working.
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

CHECKPOINTS = [0, 15, 30, 45, 60, 75, 90]
LIVE_CPS = [t for t in CHECKPOINTS if t < 90]       # 90' is one-hot for everyone
HOLDOUT = {"EPL": "2025-26", "LaLiga": "2025-26", "WC": "2026"}
VALIDATION = {"EPL": "2024-25", "LaLiga": "2024-25", "WC": "2022"}

# Search grids for the staged (greedy coordinate) tune on `val`.
W_GRID = [0.0, 0.05, 0.10, 0.20, 0.35]
WINDOW_GRID = [10, 15, 20, 30]
B_LEAD_GRID = [-0.15, -0.10, -0.05, 0.0, 0.05]
B_TRAIL_GRID = [0.0, 0.10, 0.15, 0.20, 0.25, 0.30]
RHO_GRID = [0.0, 0.03, 0.05, 0.08, 0.12]
K_GRID = [1, 2, 4, 8]
DECAY_GRID = [0.5, 0.6, 0.7, 0.8, 0.9]
RELIABILITY_BINS = 10


# ------------------------------------------------------------------ fitting

def season_age(competition, season, latest):
    """Whole seasons between `season` and the latest one in the fit set.
    Leagues age one step per season ("2024-25" is 1 behind "2025-26");
    World Cup editions age one step per 4-year cycle."""
    if competition == "WC":
        return (int(latest) - int(season)) // 4
    return int(latest[:4]) - int(season[:4])


def fit(matches, k, decay=0.8):
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


# ------------------------------------------------------- per-match precompute

def precompute(M):
    """Attach market-clock lookups used by every evaluation pass.

    Everything here is on the 90-minute market clock (model.effective_min):
    stoppage folds into 90', extra time is excluded. Prefix sums make
    "xG in the last N minutes" an O(1) subtraction instead of a scan over
    the shot list, which is what makes a full grid search affordable."""
    het = M["has_extra_time"]
    per_min = {"home": [0.0] * 91, "away": [0.0] * 91}
    for s in M["shots"]:
        m = model.effective_min(s["min"], het)
        if m is not None:
            per_min[s["team"]][m] += s["xg"]
    M["_pre"] = {}
    for side in ("home", "away"):
        acc, prefix = 0.0, []
        for t in range(91):
            acc += per_min[side][t]
            prefix.append(acc)
        M["_pre"][side] = prefix            # xG in minutes 0..t inclusive

    goals = []
    for g in M["goals"]:
        m = model.effective_min(g["min"], het)
        if m is not None:
            goals.append((g["team"], m))
    M["_goals"] = goals
    M["_score"] = {}
    for t in range(91):
        h = sum(1 for tm, m in goals if tm == "home" and m <= t)
        a = sum(1 for tm, m in goals if tm == "away" and m <= t)
        M["_score"][t] = (h, a)
    h90, a90 = M["_score"][90]
    M["_outcome"] = ((1.0, 0.0, 0.0) if h90 > a90
                     else (0.0, 1.0, 0.0) if h90 == a90 else (0.0, 0.0, 1.0))

    M["_reds"] = {"home": [], "away": []}
    for side, minute in M.get("reds") or []:
        m = model.effective_min(minute, het)
        if m is not None:
            M["_reds"][side].append(m)
    # Dismissal COUNTS are reliable even where the minute is not, so corpus
    # statistics count these and the model uses only the timed ones.
    M["_red_counts"] = tuple(M.get("red_counts") or (0, 0))
    return M


def xg_window(M, side, t, window):
    """xG a side generated in the (t - window, t] market-clock window."""
    prefix = M["_pre"][side]
    hi = min(90, int(t))
    lo = int(t) - window
    return prefix[hi] - (prefix[lo] if lo >= 0 else 0.0)


def reds_at(M, t):
    """(home reds, away reds) shown by minute t."""
    return (sum(1 for m in M["_reds"]["home"] if m <= t),
            sum(1 for m in M["_reds"]["away"] if m <= t))


def build_profile(matches):
    """Empirical remaining-scoring curve: profile[t] = the share of a
    match's xG that is still to come after minute t, averaged over the fit
    population. profile[0] = 1.0 and profile[90] = 0.0 by construction.

    This replaces the straight line (90 - t) / 90. Football does not
    distribute its chances evenly — the opening ten minutes are quiet and
    the closing twenty are not — so the linear clock systematically
    over-values early time and under-values late time."""
    per_min = [0.0] * 91
    for M in matches:
        for side in ("home", "away"):
            prefix = M["_pre"][side]
            for t in range(91):
                per_min[t] += prefix[t] - (prefix[t - 1] if t else 0.0)
    total = sum(per_min)
    if total <= 0:
        return None
    profile, remaining = [], total
    for t in range(91):
        remaining -= per_min[t]              # xG struck strictly after t
        profile.append(max(0.0, remaining / total))
    return profile


def fit_red_effect(matches, F, profile, min_time_left=10):
    """Measure the red-card multipliers directly from post-dismissal xG.

    For every match with exactly one dismissal at a KNOWN minute, compare
    what each side actually created after the card with what the model
    expected over the same window (its pre-match rate times the
    remaining-scoring share). The ratio of the two totals is the
    multiplier. This is a measurement, not a tune: red cards land in ~14%
    of matches and mostly late, so a Brier search over them reads noise,
    while the xG response is direct and has an obvious sign.

    On the current corpora this returns n = 0, and that is the honest
    answer rather than a failure: the scraped files record that a player
    was sent off but not when (corpus.red_cards), so there is no minute to
    measure against. The multipliers stay neutral until a source supplies
    dismissal minutes — the model carries the hook (model.red_card_factors)
    and the pipeline carries the incident, so the day a feed provides them
    nothing else has to change.

    Returns (self_factor, opp_factor, n_matches)."""
    act = {"self": 0.0, "opp": 0.0}
    exp = {"self": 0.0, "opp": 0.0}
    n = 0
    for M in matches:
        cards = [(side, m) for side in ("home", "away") for m in M["_reds"][side]]
        if len(cards) != 1:
            continue                         # keep the clean single-card case
        side, minute = cards[0]
        if minute > 90 - min_time_left:
            continue                         # too little left to measure
        other = "away" if side == "home" else "home"
        lam_h, lam_a = match_lams(F, M)
        lam = {"home": lam_h, "away": lam_a}
        frac = model.remaining_fraction(minute, profile)
        prefix_end = M["_pre"]
        for role, team in (("self", side), ("opp", other)):
            act[role] += prefix_end[team][90] - prefix_end[team][minute]
            exp[role] += lam[team] * frac
        n += 1
    if not n:
        return 1.0, 1.0, 0
    return (act["self"] / exp["self"] if exp["self"] else 1.0,
            act["opp"] / exp["opp"] if exp["opp"] else 1.0, n)


# --------------------------------------------------------------- evaluation

def build_model(F, M, cfg, profile):
    lam_h, lam_a = match_lams(F, M)
    red = cfg.get("red") or {}
    return model.InPlayModel(
        lam_h, lam_a, w=cfg.get("w", 0.05),
        profile=profile if cfg.get("profile", True) else None,
        window=cfg.get("window", 15), rho=cfg.get("rho", 0.0),
        b_lead=cfg.get("b_lead", 0.0), b_trail=cfg.get("b_trail", 0.0),
        red_self=red.get("self", 1.0), red_opp=red.get("opp", 1.0))


def evaluate(matches, F, cfg, profile, constant=None, reliability=False):
    """Score a configuration on a match set.

    Returns a dict with per-checkpoint Brier and log loss, their means over
    the live checkpoints (90' is one-hot for every model and carries no
    information), per-competition Brier, and optionally reliability bins
    pooled over the live checkpoints.

    constant=(pH,pD,pA) scores that fixed triple instead of the model — the
    same number at every checkpoint, it never looks at the pitch."""
    brier = {t: 0.0 for t in CHECKPOINTS}
    logloss = {t: 0.0 for t in CHECKPOINTS}
    comp_brier, comp_n = {}, {}
    bins = [[0.0, 0.0, 0] for _ in range(RELIABILITY_BINS)]
    for M in matches:
        c = M["competition"]
        cb = comp_brier.setdefault(c, {t: 0.0 for t in CHECKPOINTS})
        comp_n[c] = comp_n.get(c, 0) + 1
        target = M["_outcome"]
        live = None if constant is not None else build_model(F, M, cfg, profile)
        window = cfg.get("window", 15)
        for t in CHECKPOINTS:
            if constant is not None:
                probs = constant
            else:
                h, a = M["_score"][t]
                red_h, red_a = reds_at(M, t)
                p = live.probs(t, h, a, xg_window(M, "home", t, window),
                               xg_window(M, "away", t, window), red_h, red_a)
                probs = (p["pH"], p["pD"], p["pA"])
            b = sum((pi - oi) ** 2 for pi, oi in zip(probs, target))
            brier[t] += b
            cb[t] += b
            logloss[t] += -math.log(max(probs[target.index(1.0)], 1e-12))
            if reliability and t in LIVE_CPS and t > 0:
                for pi, oi in zip(probs, target):
                    idx = min(RELIABILITY_BINS - 1, int(pi * RELIABILITY_BINS))
                    bins[idx][0] += pi
                    bins[idx][1] += oi
                    bins[idx][2] += 1
    n = float(len(matches))
    out = {
        "brier": {t: brier[t] / n for t in CHECKPOINTS},
        "logloss": {t: logloss[t] / n for t in CHECKPOINTS},
        "per_competition": {c: {t: comp_brier[c][t] / comp_n[c]
                                for t in CHECKPOINTS} for c in comp_brier},
        "n": comp_n,
    }
    out["mean_brier"] = sum(out["brier"][t] for t in LIVE_CPS) / len(LIVE_CPS)
    out["mean_logloss"] = sum(out["logloss"][t] for t in LIVE_CPS) / len(LIVE_CPS)
    if reliability:
        total = sum(b[2] for b in bins) or 1
        rel, ece = [], 0.0
        for pred_sum, act_sum, cnt in bins:
            if not cnt:
                rel.append(None)
                continue
            pred, act = pred_sum / cnt, act_sum / cnt
            ece += abs(pred - act) * cnt / total
            rel.append({"pred": round(pred, 4), "actual": round(act, 4), "n": cnt})
        out["reliability"] = rel
        out["ece"] = ece
    return out


def outcome_90(M):
    """One-hot (H, D, A) of the 90-minute result."""
    return M["_outcome"]


def base_rates(matches):
    """Global (pH, pD, pA) frequency of 90-minute outcomes — the
    "always quote 0.45/0.24/0.31" constant baseline."""
    counts = [0, 0, 0]
    for M in matches:
        counts[M["_outcome"].index(1.0)] += 1
    n = float(len(matches))
    return tuple(c / n for c in counts)


def split_by(matches, table):
    """(rest, selected) split on a {competition: season} table."""
    rest, selected = [], []
    for M in matches:
        (selected if M["season"] == table.get(M["competition"]) else rest).append(M)
    return rest, selected


# ------------------------------------------------------------------- tuning

def tune(inner, val, verbose=True):
    """Staged coordinate search for the model shape, scored on `val` with
    ratings fit on `inner`. Each stage keeps the best value found so far and
    moves on, which is enough for a search space this smooth and keeps the
    whole tune to a few thousand evaluations."""
    F = fit(inner, k=1)
    profile = build_profile(inner)
    cfg = {"w": 0.0, "window": 15, "profile": False, "rho": 0.0,
           "b_lead": 0.0, "b_trail": 0.0}
    trace = []

    def score(candidate):
        return evaluate(val, F, candidate, profile)["mean_brier"]

    def stage(name, options):
        """Try each override dict; keep the best if it beats the incumbent."""
        best, winner = score(cfg), None
        for override in options:
            trial = dict(cfg)
            trial.update(override)
            s = score(trial)
            if s < best:
                best, winner = s, override
        if winner:
            cfg.update(winner)
        trace.append({"stage": name, "val_brier": round(best, 5),
                      "chosen": dict(winner or {})})
        if verbose:
            kept = (", ".join("%s=%s" % (k, winner[k]) for k in sorted(winner))
                    if winner else "no change")
            print("  %-14s val Brier %.5f  ->  %s" % (name, best, kept))
        return best

    if verbose:
        print("tuning on val (%d matches), ratings from inner (%d):"
              % (len(val), len(inner)))
        print("  %-14s val Brier %.5f  (linear clock, no momentum)"
              % ("start", score(cfg)))
    stage("clock", [{"profile": True}])
    stage("momentum", [{"w": w, "window": win} for w in W_GRID
                       for win in (WINDOW_GRID if w else [15])])
    stage("score state", [{"b_lead": bl, "b_trail": bt}
                          for bl in B_LEAD_GRID for bt in B_TRAIL_GRID])
    stage("draw (rho)", [{"rho": r} for r in RHO_GRID])

    # Red-card multipliers are measured, not tuned (see fit_red_effect).
    red_self, red_opp, n_red = fit_red_effect(inner, F, profile)
    cfg["red"] = {"self": round(red_self, 4), "opp": round(red_opp, 4),
                  "n": n_red}
    if verbose:
        if n_red:
            print("  %-14s measured from %d single-card matches: self x%.3f, "
                  "opponent x%.3f" % ("red cards", n_red, red_self, red_opp))
        else:
            print("  %-14s NOT FIT: the corpus records dismissals but not "
                  "their minute" % "red cards")
            print("  %-14s multipliers left neutral; the model and feed carry "
                  "the hook" % "")

    # Rating hypers last: they change the fit, so re-fit inside the loop.
    best = (None, None, None)
    for k in K_GRID:
        for decay in DECAY_GRID:
            Fk = fit(inner, k, decay=decay)
            prof_k = build_profile(inner)
            s = evaluate(val, Fk, cfg, prof_k)["mean_brier"]
            if best[0] is None or s < best[0]:
                best = (s, k, decay)
    _, k_best, decay_best = best
    trace.append({"stage": "ratings", "val_brier": round(best[0], 5),
                  "chosen": {"k": k_best, "decay": decay_best}})
    if verbose:
        print("  %-14s val Brier %.5f  ->  k=%d, decay=%.1f"
              % ("ratings", best[0], k_best, decay_best))
    return cfg, k_best, decay_best, trace


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
            "reds": [(c["team"], c["min"]) for c in (raw.get("cards") or [])
                     if (c.get("type") or "").lower() == "red"
                     and c.get("min") is not None],
            "red_counts": (sum(1 for c in (raw.get("cards") or [])
                               if (c.get("type") or "").lower() == "red"
                               and c.get("team") == "home"),
                           sum(1 for c in (raw.get("cards") or [])
                               if (c.get("type") or "").lower() == "red"
                               and c.get("team") == "away")),
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


def write_params(out_path, F, cfg, profile, brier_block, generated_from):
    params = {
        "version": 3,
        "mu": {c: round(v, 4) for c, v in sorted(F["mu"].items())},
        "hfa": round(F["hfa"], 4),
        "k": F["k"],
        "decay": F["decay"],
        "w": cfg["w"],
        "window": cfg["window"],
        "rho": cfg["rho"],
        "b_lead": cfg["b_lead"],
        "b_trail": cfg["b_trail"],
        "red": cfg.get("red") or {"self": 1.0, "opp": 1.0, "n": 0},
        "profile": [round(p, 6) for p in profile] if cfg.get("profile") else None,
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


DASHBOARDS = {
    "EPL": ("epl_dashboard", "xepl"),
    "LaLiga": ("laliga_dashboard", "xlaliga"),
    "WC": ("wc2026_dashboard", "xworldcuptwit"),
}


def dashboard_targets(roots, repo_root=REPO):
    """[(competition, dashboard dir)] to write params into.

    Both the corpus root the fit was read from AND this repo's vendored
    projects/ copy, because the portfolio now serves the vendored one — a
    refit that updated only the source clone would leave the published
    dashboards quoting stale numbers. Deduped by resolved path so a run
    whose corpus root IS the vendored copy writes once."""
    out, seen = [], set()
    for comp, (dash, vendor) in DASHBOARDS.items():
        for root in (roots.get(comp), repo_root / "projects" / vendor):
            if root is None:
                continue
            path = Path(root) / dash
            if not path.is_dir():
                continue
            key = str(path.resolve())
            if key not in seen:
                seen.add(key)
                out.append((comp, path))
    return out


def write_dashboard_params(roots, F, cfg, profile):
    """One winprob_params.js per scraper dashboard, with that competition's
    teams only (names WITHOUT the namespace prefix). The WC dashboard gets
    hfa 1.0 and a neutral flag — every World Cup venue is neutral."""
    written = []
    for comp, dash_dir in dashboard_targets(roots):
        if comp not in F["mu"]:
            continue
        neutral = comp == "WC"
        teams = {key.split("/", 1)[1]: {"att": round(t["att"], 4),
                                        "def": round(t["def"], 4)}
                 for key, t in F["teams"].items()
                 if key.startswith(comp + "/")}
        payload = {
            "version": 3,
            "competition": comp,
            "mu": round(F["mu"][comp], 4),
            "hfa": 1.0 if neutral else round(F["hfa"], 4),
            "neutral": neutral,
            "w": cfg["w"],
            "window": cfg["window"],
            "rho": cfg["rho"],
            "bLead": cfg["b_lead"],
            "bTrail": cfg["b_trail"],
            "red": cfg.get("red") or {"self": 1.0, "opp": 1.0},
            "profile": [round(p, 5) for p in profile] if cfg.get("profile") else None,
            "maxGoals": model.MAX_GOALS,
            "lamFloor": model.LAM_FLOOR,
            "teams": teams,
        }
        out = dash_dir / "winprob_params.js"
        text = ("// generated by rshiri.github.io/live-pipeline/tradepipe/"
                "calibrate.py - do not edit by hand\n"
                "window.WINPROB_PARAMS = %s;\n"
                % json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        out.write_text(text, encoding="utf-8")
        written.append(out)
        print("wrote %s (%.1f KB, %d teams)" % (out, out.stat().st_size / 1024,
                                                len(teams)))
        # Ship the model itself alongside its parameters, so a dashboard can
        # never end up running last year's maths against this year's numbers.
        source = HERE.parent / "web" / "winprob_model.js"
        if source.is_file():
            (dash_dir / "winprob_model.js").write_text(
                source.read_text(encoding="utf-8"), encoding="utf-8")
    return written


# -------------------------------------------------------------------- main

def print_table(title, rows, n_eval):
    print(title + " (n=%d matches)" % n_eval)
    print("  min  " + "".join("%12s" % name for name, _ in rows))
    for t in CHECKPOINTS:
        print("  %3d  " % t + "".join("%12.4f" % vals[t] for _, vals in rows))


def main():
    ap = argparse.ArgumentParser(
        description="Fit win-prob model params from all scraped corpora.")
    ap.add_argument("--epl", help="XEPL repo root (default: sibling clone, /workspace/xepl, or projects/xepl)")
    ap.add_argument("--laliga", help="XLALIGA repo root (default: sibling clone, /workspace/xlaliga, or projects/xlaliga)")
    ap.add_argument("--wc", help="XWORLDCUPTWIT repo root (default: sibling clone, /workspace/xworldcuptwit, or projects/xworldcuptwit)")
    ap.add_argument("--data", default=str(REPO / "assets" / "data" / "argentina"),
                    help="fallback argentina match dir when no corpora found")
    ap.add_argument("--out", default=str(REPO / "assets" / "data" / "winprob" / "model_params.json"),
                    help="output params file (default: assets/data/winprob/model_params.json)")
    ap.add_argument("--no-dashboards", action="store_true",
                    help="skip writing winprob_params.js into the dashboards")
    args = ap.parse_args()

    corpora, roots = corpus.default_corpora(args.epl, args.laliga, args.wc,
                                            repo_root=REPO)
    if corpora:
        matches = [precompute(M) for M in corpus.iter_matches(corpora)]
        run_full(args, matches, roots)
    else:
        print("WARNING: no scraper corpora found (../XEPL, ../XLALIGA, "
              "../XWORLDCUPTWIT, /workspace equivalents, or the vendored "
              "projects/ copies).")
        print("WARNING: falling back to the 8 argentina match JSONs -- "
              "params will cover competition 'WC' only and the Brier "
              "numbers are an in-sample smoke test, not a benchmark.")
        matches = [precompute(M) for M in load_argentina(Path(args.data))]
        run_fallback(args, matches)


def run_full(args, matches, roots):
    n_shots = sum(len(M["shots"]) for M in matches)
    n_reds = sum(1 for M in matches if sum(M["_red_counts"]))
    n_timed = sum(1 for M in matches if M["_reds"]["home"] or M["_reds"]["away"])
    print("total: %d matches, %d shots, %d with a red card (%d with a known "
          "dismissal minute)" % (len(matches), n_shots, n_reds, n_timed))
    print()

    train, held = split_by(matches, HOLDOUT)
    inner, val = split_by(train, VALIDATION)
    print("protocol: inner %d (tune-time ratings) | val %d (chooses every "
          "hyper) | train %d (inner+val, final ratings) | holdout %d "
          "(scored once)" % (len(inner), len(val), len(train), len(held)))
    print()

    cfg, k_best, decay_best, trace = tune(inner, val)
    print()

    # ---- the single holdout evaluation ----
    F_train = fit(train, k_best, decay=decay_best)
    profile = build_profile(train)
    # Red multipliers are a property of the data, not of the split: re-measure
    # on the full training block now that its ratings are the final ones.
    red_self, red_opp, n_red = fit_red_effect(train, F_train, profile)
    cfg["red"] = {"self": round(red_self, 4), "opp": round(red_opp, 4), "n": n_red}

    const = base_rates(train)
    v3 = evaluate(held, F_train, cfg, profile, reliability=True)
    v2_cfg = {"w": 0.35, "window": 15, "profile": False, "rho": 0.0,
              "b_lead": 0.0, "b_trail": 0.0}
    F_v2 = fit(train, 1, decay=0.8)
    v2 = evaluate(held, F_v2, v2_cfg, None, reliability=True)
    w0 = evaluate(held, F_v2, dict(v2_cfg, w=0.0), None)
    constant = evaluate(held, F_v2, v2_cfg, None, constant=const)

    print("constant baseline (train outcome rates): H %.3f / D %.3f / A %.3f"
          % const)
    print_table("mean Brier vs the 90-minute outcome, HOLDOUT (scored once)",
                [("v3", v3["brier"]), ("v2 (w=.35)", v2["brier"]),
                 ("v2 w=0", w0["brier"]), ("constant", constant["brier"])],
                len(held))
    print("  mean over live checkpoints: v3 %.5f | v2 %.5f | v2 w=0 %.5f | "
          "constant %.5f" % (v3["mean_brier"], v2["mean_brier"],
                             w0["mean_brier"], constant["mean_brier"]))
    print("  mean log loss:              v3 %.5f | v2 %.5f | v2 w=0 %.5f"
          % (v3["mean_logloss"], v2["mean_logloss"], w0["mean_logloss"]))
    print("  calibration error (ECE):    v3 %.4f | v2 %.4f"
          % (v3["ece"], v2["ece"]))
    print()
    for c in sorted(v3["n"]):
        print("  %-7s n=%3d   v3 %.5f   v2 %.5f   (%+.5f)"
              % (c, v3["n"][c],
                 sum(v3["per_competition"][c][t] for t in LIVE_CPS) / len(LIVE_CPS),
                 sum(v2["per_competition"][c][t] for t in LIVE_CPS) / len(LIVE_CPS),
                 sum(v3["per_competition"][c][t] - v2["per_competition"][c][t]
                     for t in LIVE_CPS) / len(LIVE_CPS)))
    print()
    print("  reliability (predicted -> actual, pooled 15'-75'):")
    for tag, res in (("v2", v2), ("v3", v3)):
        cells = " ".join("%.2f/%.2f" % (b["pred"], b["actual"]) if b else "  -  "
                         for b in res["reliability"])
        print("    %-3s ECE %.4f  %s" % (tag, res["ece"], cells))
    print()

    # ---- production fit: everything, chosen hypers ----
    F = fit(matches, k_best, decay=decay_best)
    profile_all = build_profile(matches)
    red_self, red_opp, n_red = fit_red_effect(matches, F, profile_all)
    cfg["red"] = {"self": round(red_self, 4), "opp": round(red_opp, 4), "n": n_red}
    print("production fit on all %d matches:" % len(matches))
    print("  mu  " + "  ".join("%s %.4f" % (c, F["mu"][c])
                               for c in sorted(F["mu"])))
    print("  hfa %.4f   k %d   decay %.2f   teams %d"
          % (F["hfa"], F["k"], F["decay"], len(F["teams"])))
    print("  w %.2f  window %d  rho %.2f  b_lead %+.2f  b_trail %+.2f  "
          "red self x%.2f opp x%.2f"
          % (cfg["w"], cfg["window"], cfg["rho"], cfg["b_lead"],
             cfg["b_trail"], cfg["red"]["self"], cfg["red"]["opp"]))

    brier_block = {
        "design": "three disjoint blocks in time: ratings for tuning fit on "
                  "2022-23..2023-24 leagues + WC2018, every hyper chosen on "
                  "2024-25 leagues + WC2022, holdout (2025-26 leagues + "
                  "WC2026) scored exactly once by the finished config; "
                  "production rates refit on all data",
        "checkpoints": CHECKPOINTS,
        "model": [round(v3["brier"][t], 4) for t in CHECKPOINTS],
        "baseline_v2": [round(v2["brier"][t], 4) for t in CHECKPOINTS],
        "baseline_w0": [round(w0["brier"][t], 4) for t in CHECKPOINTS],
        "constant": [round(constant["brier"][t], 4) for t in CHECKPOINTS],
        "constant_probs": [round(p, 4) for p in const],
        "logloss": [round(v3["logloss"][t], 4) for t in CHECKPOINTS],
        "logloss_baseline_v2": [round(v2["logloss"][t], 4) for t in CHECKPOINTS],
        "mean_brier": {"model": round(v3["mean_brier"], 5),
                       "baseline_v2": round(v2["mean_brier"], 5),
                       "baseline_w0": round(w0["mean_brier"], 5),
                       "constant": round(constant["mean_brier"], 5)},
        "mean_logloss": {"model": round(v3["mean_logloss"], 5),
                         "baseline_v2": round(v2["mean_logloss"], 5)},
        "ece": {"model": round(v3["ece"], 4), "baseline_v2": round(v2["ece"], 4)},
        "reliability": {"model": v3["reliability"], "baseline_v2": v2["reliability"]},
        "n_eval": len(held),
        "tuning_trace": trace,
        "per_competition": {
            c: {"model": [round(v3["per_competition"][c][t], 4) for t in CHECKPOINTS],
                "baseline_v2": [round(v2["per_competition"][c][t], 4) for t in CHECKPOINTS],
                "baseline_w0": [round(w0["per_competition"][c][t], 4) for t in CHECKPOINTS],
                "constant": [round(constant["per_competition"][c][t], 4) for t in CHECKPOINTS],
                "n": v3["n"][c]}
            for c in sorted(v3["n"])},
    }
    write_params(Path(args.out), F, cfg, profile_all, brier_block,
                 corpus_summary(matches))
    if not args.no_dashboards:
        write_dashboard_params(roots, F, cfg, profile_all)


def run_fallback(args, matches):
    """No corpora: fit the 8 argentina files so the demo still prices."""
    F = fit(matches, k=1)
    profile = build_profile(matches)
    cfg = {"w": model.DEFAULT_W, "window": 15, "profile": True, "rho": 0.0,
           "b_lead": 0.0, "b_trail": 0.0,
           "red": {"self": 1.0, "opp": 1.0, "n": 0}}
    res = evaluate(matches, F, cfg, profile)
    w0 = evaluate(matches, F, dict(cfg, w=0.0), profile)

    print("fitted %d teams from %d matches, mu_WC = %.4f xG per team-match"
          % (len(F["teams"]), len(matches), F["mu"]["WC"]))
    print_table("mean in-sample Brier (smoke test only)",
                [("model", res["brier"]), ("w=0", w0["brier"])], len(matches))

    brier_block = {
        "design": "in-sample on the 8 argentina matches (fallback mode; "
                  "no holdout possible)",
        "checkpoints": CHECKPOINTS,
        "model": [round(res["brier"][t], 4) for t in CHECKPOINTS],
        "baseline_w0": [round(w0["brier"][t], 4) for t in CHECKPOINTS],
        "logloss": [round(res["logloss"][t], 4) for t in CHECKPOINTS],
        "n_eval": len(matches),
    }
    write_params(Path(args.out), F, cfg, profile, brier_block,
                 ["fallback: assets/data/argentina (8 matches)"])


if __name__ == "__main__":
    main()
