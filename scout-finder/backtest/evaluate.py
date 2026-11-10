"""Does what we know in season t predict whether a transfer works out?

  python -m backtest.evaluate          # train only, 5-fold CV, writes data/backtest_train.json
  python -m backtest.evaluate --test   # fit on train, score the test pair (at the season's end)

2026-27 is unfinished, so Ram's call is to build the test path but report nothing from
it yet. Run transfers --test and this --test once the season is over.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA = Path(__file__).resolve().parent.parent / "data"
NUMERIC = ["prev_share", "age", "log_value", "rating", "log_prev_minutes", "score", "league_gap"]
TRAIN_SEASON = "2024-25"
TEST_SEASON = "2025-26"


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    out = df[df["status"] == "moved"].copy()
    out["log_value"] = np.log1p(out["value_eur"])
    out["log_prev_minutes"] = np.log1p(out["prev_minutes"])
    out["pos_group"] = out["pos_group"].fillna("unknown")
    return out.reset_index(drop=True)


def share_only():
    return make_pipeline(ColumnTransformer([("share", StandardScaler(), ["prev_share"])]), LogisticRegression())


def full_model():
    numeric = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler())
    cols = ColumnTransformer([("num", numeric, NUMERIC),
                              ("pos", OneHotEncoder(handle_unknown="ignore"), ["pos_group"])])
    return make_pipeline(cols, LogisticRegression(max_iter=2000))


def fit_predict(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, np.ndarray]:
    y = train["success"].astype(int)
    return {"base_rate": np.full(len(test), y.mean()),
            "prev_share": share_only().fit(train, y).predict_proba(test)[:, 1],
            "model": full_model().fit(train, y).predict_proba(test)[:, 1]}


def out_of_fold(df: pd.DataFrame, seed: int = 0) -> dict[str, np.ndarray]:
    """Grouped by destination club: teammates' outcomes must not sit on both sides of a fold."""
    preds = {k: np.zeros(len(df)) for k in ("base_rate", "prev_share", "model")}
    folds = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    for tr, te in folds.split(df, df["success"].astype(int), df["new_team_id"]):
        for name, p in fit_predict(df.iloc[tr], df.iloc[te]).items():
            preds[name][te] = p
    return preds


def scores(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {"brier": brier_score_loss(y, p), "log_loss": log_loss(y, p),
            "auc": roc_auc_score(y, p) if np.ptp(p) > 0 else 0.5}


def paired_gap(y: np.ndarray, a: np.ndarray, b: np.ndarray, n: int = 2000, seed: int = 0) -> dict[str, list[float]]:
    """90% bootstrap interval of score(a) - score(b), resampling players."""
    rng = np.random.default_rng(seed)
    gaps = {"brier": [], "auc": []}
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        sa, sb = scores(y[i], a[i]), scores(y[i], b[i])
        for k in gaps:
            gaps[k].append(sa[k] - sb[k])
    return {k: [float(x) for x in np.percentile(v, [5, 95])] for k, v in gaps.items()}


def calibration(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    order = pd.qcut(p, bins, labels=False, duplicates="drop")
    return [{"predicted": float(p[order == b].mean()), "observed": float(y[order == b].mean()),
             "n": int((order == b).sum())} for b in np.unique(order)]


def rate_by(df: pd.DataFrame, labels: pd.Series, order: list[str]) -> list[dict]:
    g = df.groupby(labels)["success"].agg(["mean", "size"])
    return [{"label": k, "rate": float(g.loc[k, "mean"]), "n": int(g.loc[k, "size"])} for k in order if k in g.index]


def describe(df: pd.DataFrame) -> dict:
    direction = pd.Series(np.select([df["new_league"] == df["prev_league"], df["league_gap"] > 0],
                                    ["same", "up"], "down"), index=df.index)
    age = pd.cut(df["age"], [0, 21, 25, 29, 99], labels=["<=21", "22-25", "26-29", "30+"]).astype("string").fillna("unknown")
    value = pd.cut(df["value_eur"], [-1, 1e6, 5e6, 15e6, 1e12], labels=["<1m", "1-5m", "5-15m", "15m+"]).astype("string").fillna("unknown")
    return {"direction": rate_by(df, direction, ["up", "same", "down"]),
            "age": rate_by(df, age, ["<=21", "22-25", "26-29", "30+"]),
            "value": rate_by(df, value, ["<1m", "1-5m", "5-15m", "15m+", "unknown"])}


def coefficients(df: pd.DataFrame) -> dict[str, float]:
    m = full_model().fit(df, df["success"].astype(int))
    names = m[0].get_feature_names_out()
    return {str(n).split("__")[-1]: float(c) for n, c in zip(names, m[-1].coef_[0])}


def report(df: pd.DataFrame, all_rows: pd.DataFrame) -> dict:
    y = df["success"].astype(int).to_numpy()
    p = out_of_fold(df)
    veteran = (df["prev_minutes"] >= 900).to_numpy()
    counts = all_rows["status"].value_counts().to_dict()
    return {
        "season_t": TRAIN_SEASON, "season_t1": "2025-26", "evaluation": "5-fold CV grouped by destination club",
        "counts": {k: int(v) for k, v in counts.items()}, "transfers": len(df), "success_rate": float(y.mean()),
        "successes_under_5_games": int(((y == 1) & (df["new_games_since"] < 5).to_numpy()).sum()),
        "metrics": {k: scores(y, v) for k, v in p.items()},
        "metrics_900_plus": {"n": int(veteran.sum()), "success_rate": float(y[veteran].mean()),
                             **{k: scores(y[veteran], v[veteran]) for k, v in p.items()}},
        "model_minus_prev_share": paired_gap(y, p["model"], p["prev_share"]),
        "calibration": calibration(y, p["model"]),
        "by": describe(df),
        "coefficients": coefficients(df),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="score the test pair (at the season's end)")
    a = ap.parse_args()
    rows = pd.read_csv(DATA / "transfers.csv")
    train = prepare(rows[rows["season_t"] == TRAIN_SEASON])
    if a.test:
        test = prepare(rows[rows["season_t"] == TEST_SEASON])
        y = test["success"].astype(int).to_numpy()
        for name, p in fit_predict(train, test).items():
            print(name, scores(y, p))
        return
    out = report(train, rows[rows["season_t"] == TRAIN_SEASON])
    (DATA / "backtest_train.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "calibration"}, indent=1))
    for row in out["calibration"]:
        print(row)


if __name__ == "__main__":
    main()
