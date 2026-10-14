"""Ram's own xG / xA model (XEPL, XLALIGA) in place of FotMob's for the leagues it covers.

XEPL and XLALIGA score every shot with xg_core v3 (and passes with a retrained xA
model) from WhoScored events, and ship per-season player totals in
<dashboard>/data/<season>.js (window.LL_PLAYERS[season]). Their player ids are
WhoScored's, but each photo URL carries the FotMob id, which is the join key.

Ram's model runs about 10-17% above FotMob's xG overall (different calibration),
so mixing the raw numbers would lift every EPL / LaLiga player in the
cross-league percentiles. Instead Ram's model decides how a league's xG is shared
out between its players, and the league total is scaled to FotMob's, the common
yardstick for all 12 leagues. The scale is reported in meta.xg_scale.

Progressive passes / carries and xT added exist only in these two leagues, so
they ride along as extras, not as cross-league metrics.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

DESKTOP = Path.home() / "OneDrive" / "שולחן העבודה"
DEFAULT_DIRS = {
    "ENG1": DESKTOP / "XEPL" / "epl_dashboard" / "data",
    "ESP1": DESKTOP / "XLALIGA" / "laliga_dashboard" / "data",
}
MODEL = {"xg": "xg", "npxg": "npxg", "xa": "xa"}          # XEPL field -> our column
EXTRAS = {"prog_passes": "prog_passes", "prog_carries": "prog_carries"}
_FOTMOB_ID = re.compile(r"playerimages/(\d+)\.png")


def load_bundle(path: Path, season: str) -> pd.DataFrame:
    """One season's players from an XEPL/XLALIGA bundle, keyed by FotMob id."""
    prefix = f'window.LL_PLAYERS["{season}"]='
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            players = json.loads(line[len(prefix):].rstrip(";"))
            break
    else:
        return pd.DataFrame()
    rows = []
    for p in players:
        m = _FOTMOB_ID.search(p.get("photo") or "")
        if not m or not p.get("mins"):
            continue
        row = {"fotmob_id": m.group(1), "ram_minutes": float(p["mins"]),
               "xt_added_p90": p.get("xt_added_p90")}
        row.update({f"ram_{k}": p.get(k) for k in MODEL})
        row.update({k: p.get(k) for k in EXTRAS if k in p})
        rows.append(row)
    df = pd.DataFrame(rows)
    # The same FotMob id twice (a mid-season move inside the league): add up.
    return df.groupby("fotmob_id", as_index=False).sum(min_count=1) if len(df) else df


def apply(df: pd.DataFrame, dirs: dict[str, Path] | None = None) -> tuple[pd.DataFrame, dict, dict]:
    """Swap in Ram's model where a bundle covers the league-season.

    Returns (df, xg_source per league, xg_scale per league-season).
    Totals are re-expressed over our FotMob minutes: rate from Ram's minutes,
    times the minutes FotMob counted, so per-90s stay consistent with every
    other column.
    """
    dirs = DEFAULT_DIRS if dirs is None else dirs
    df = df.copy()
    source = {lg: "fotmob" for lg in df["league"].unique()}
    scale = {}
    fid = df["player_id"].str.extract(r"^fotmob:(\d+)")[0]
    for (league, season), idx in df.groupby(["league", "season"]).groups.items():
        path = dirs.get(league, Path()) / f"{season}.js"
        if league not in dirs or not path.exists():
            continue
        ram = load_bundle(path, season)
        if ram.empty:
            continue
        sub = df.loc[idx].assign(fotmob_id=fid.loc[idx]).merge(ram, on="fotmob_id", how="left")
        sub.index = idx
        hit = sub["ram_minutes"].notna()
        if hit.mean() < 0.8:          # a bad join must not half-replace a league
            print(f"ram_xg: {league} {season} only {hit.mean():.0%} matched; kept FotMob")
            continue
        per_min = sub["minutes"] / sub["ram_minutes"]
        for k, col in MODEL.items():
            if col not in df:
                continue
            ram_total = sub[f"ram_{k}"] * per_min
            both = hit & ram_total.notna() & df.loc[idx, col].notna()
            s = df.loc[idx, col][both].sum() / ram_total[both].sum() if ram_total[both].sum() else 1
            df.loc[idx[both.to_numpy()], col] = (ram_total[both] * s).to_numpy()
            scale[f"{league} {season} {col}"] = round(float(s), 3)
        for k, col in EXTRAS.items():
            if k in sub and sub[k].notna().any():
                df.loc[idx, col] = (sub[k] * per_min).to_numpy()
        if "xt_added_p90" in sub and sub["xt_added_p90"].notna().any():
            df.loc[idx, "xt_added_p90"] = sub["xt_added_p90"].to_numpy()
        source[league] = "ram"
    return df, source, scale
