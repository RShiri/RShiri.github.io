#!/usr/bin/env python3
"""
Touchline data pipeline
=======================
Builds `players.json` — the real-player database behind the demo — by combining
three public sources and then *updating game-style attribute priors with actual
match statistics*.

Layers
------
1. ATTRIBUTE PRIOR (global)    EA FC 24 player ratings — ~15.8k players, 654 clubs,
                               155 nations. Gives FM-style attributes for players
                               all over the world, including leagues with no public
                               event data.
2. LEAGUE MAP                  FIFA 22 dataset — used only for its club -> league
                               mapping so we can filter by competition.
3. PERFORMANCE UPDATE (Big 5)  FBref advanced season stats, 3 seasons. For every
                               player we can match, attributes are re-derived from
                               observed output and blended over the prior with
                               minutes-weighted (empirical-Bayes) shrinkage.
4. VALUATION + CONTRACTS       A public pre-scraped Transfermarkt dump (values current
                               to Sept 2025). Supplies real market values, contract
                               expiry dates, height and date of birth. Transfermarkt
                               itself is not scraped here — the dataset is used as
                               published.

Players only present in FBref (recent breakthroughs missing from EA FC 24) are
included with attributes derived purely from stats.

Every player carries a `conf` tier so the UI can be honest about data quality:
  2 = verified   (recent Big-5 match data drives the ratings)
  1 = partial    (matched, but small minutes sample)
  0 = prior only (EA FC 24 baseline, no recent match data)

Run:  python3 build_players.py
"""
import io, json, os, re, sys, unicodedata, urllib.request
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
OUT = os.path.join(HERE, "players.json")
os.makedirs(CACHE, exist_ok=True)

FC24 = "https://raw.githubusercontent.com/federicopaschetta/FootballPlayersAnalysis/main/male_players.csv"
FIFA22 = "https://raw.githubusercontent.com/abineshta/FIFA-22-complete-player-dataset-EDA/main/players_22.csv"
FBREF = ("https://github.com/JaseZiv/worldfootballR_data/releases/download/"
         "fb_big5_advanced_season_stats/big5_player_{}.rds")
TM_BASE = ("https://raw.githubusercontent.com/salimt/football-datasets/main/"
           "datalake/transfermarkt")
TM_VALUES = f"{TM_BASE}/player_latest_market_value/player_latest_market_value.csv"
TM_PROFILES = f"{TM_BASE}/player_profiles/player_profiles.csv"
TM_VALHIST = f"{TM_BASE}/player_market_value/player_market_value.csv"
TM_INJURIES = f"{TM_BASE}/player_injuries/player_injuries.csv"
TM_TRANSFERS = ("https://media.githubusercontent.com/media/salimt/football-datasets/main/"
                "datalake/transfermarkt/transfer_history/transfer_history.csv")
# player_national_performances is deliberately NOT used: its team ids do not
# resolve to team names, so senior caps cannot be told apart from youth caps.
# player_performances is stored with Git LFS, so it comes from the media host
TM_PERF = ("https://media.githubusercontent.com/media/salimt/football-datasets/main/"
           "datalake/transfermarkt/player_performances/player_performances.csv")
TM_SEASONS = ["22/23", "23/24", "24/25"]     # aligns with SEASONS above
TM_LATEST = "24/25"
SNAPSHOT = pd.Timestamp("2025-01-01")   # mid-2024/25; ages are computed against this
STAT_TYPES = ["standard", "shooting", "passing", "defense", "possession", "misc"]
# The upstream FBref mirror is archived and froze ~5 games into 2025/26, so the
# latest *complete* season it carries is 2024/25 (Season_End_Year 2025). We window
# on the three complete seasons ending there rather than shipping a 5-game sample.
SEASONS = [2023, 2024, 2025]
LATEST = max(SEASONS)
AGE_OFFSET = 1                        # EA FC 24 is 2023/24; snapshot is 2024/25
SHRINK_K = 900.0                      # minutes at which stats get 50% of the weight


def fetch(url, name):
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        print(f"  downloading {name} ...", flush=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=300) as r, open(path, "wb") as f:
            f.write(r.read())
    return path


def parse_age(v):
    """FBref ages look like '20-142' (years-days); EA FC 24 gives plain ints."""
    if pd.isna(v):
        return None
    m = re.match(r"\s*(\d{1,2})", str(v))
    return int(m.group(1)) if m else None


def norm_name(s):
    """Accent/punctuation-insensitive key for joining across sources."""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z ]", " ", s).lower()
    return re.sub(r"\s+", " ", s).strip()


# FIFA position -> our 8 groups
POS_MAP = {"GK": "GK", "CB": "CB", "LB": "FB", "RB": "FB", "LWB": "FB", "RWB": "FB",
           "CDM": "DM", "CM": "CM", "CAM": "AM", "CF": "AM",
           "LW": "WG", "RW": "WG", "LM": "WG", "RM": "WG", "ST": "ST"}
LINE = {"GK": "GK", "CB": "DEF", "FB": "DEF", "DM": "MID", "CM": "MID",
        "AM": "MID", "WG": "ATT", "ST": "ATT"}
POS_LABEL = {"GK": "Goalkeeper", "CB": "Centre-back", "FB": "Full-back",
             "DM": "Defensive midfielder", "CM": "Central midfielder",
             "AM": "Attacking midfielder", "WG": "Winger", "ST": "Striker"}

# our attribute vocabulary -> EA FC 24 source column
ATTR_FROM_FC24 = {
    "pace": "Pace", "stamina": "Stamina", "strength": "Strength",
    "control": "Ball", "dribbling": "Dribbling", "passing": "Passing",
    "vision": "Vision", "finishing": "Finishing", "aerial": "Heading",
    "defending": "Defending", "pressing": "Aggression",
    "positioning": "Positioning", "composure": "Composure",
}
ATTRS = list(ATTR_FROM_FC24)


# ----------------------------------------------------------------------------
# 1. attribute priors + league map
# ----------------------------------------------------------------------------
def load_priors():
    print("[1/4] EA FC 24 attribute priors")
    fc = pd.read_csv(fetch(FC24, "fc24.csv"), low_memory=False)
    fc = fc[fc.Position.notna() & fc.Name.notna()].copy()
    fc["posg"] = fc.Position.map(POS_MAP)
    fc = fc[fc.posg.notna()]

    print("[2/4] FIFA 22 league map (by player name, then by club)")
    f22 = pd.read_csv(fetch(FIFA22, "fifa22.csv"), low_memory=False)
    f22 = f22.dropna(subset=["league_name"])
    lg = (f22.dropna(subset=["club_name"])
             .groupby("club_name").league_name.agg(lambda s: s.mode().iat[0]))
    club_league = {norm_name(k): v for k, v in lg.items()}
    # Club names differ between the two sources ("Paris SG" vs "Paris Saint-Germain"),
    # so join on player name first — names are far more stable than club strings.
    name_league = {}
    for col in ("long_name", "short_name"):
        if col in f22.columns:
            for nm, lgn in zip(f22[col], f22.league_name):
                k = norm_name(nm)
                if k:
                    name_league.setdefault(k, lgn)

    rows = []
    for r in fc.to_dict("records"):
        a = {k: float(r[c]) for k, c in ATTR_FROM_FC24.items()
             if pd.notna(r.get(c, np.nan))}
        if len(a) < len(ATTRS) - 2:
            continue
        rows.append({
            "name": r["Name"], "key": norm_name(r["Name"]),
            "club": r["Club"] if isinstance(r["Club"], str) else "—",
            "nation": r["Nation"] if isinstance(r["Nation"], str) else "—",
            "pos": r["posg"],
            "age24": int(r["Age"]) if pd.notna(r["Age"]) else None,
            "foot": r["Preferred foot"] if isinstance(r.get("Preferred foot"), str) else "Right",
            "overall": int(r["Overall"]) if pd.notna(r["Overall"]) else None,
            "gk": float(r["GK"]) if pd.notna(r["GK"]) else None,
            **{f"a_{k}": v for k, v in a.items()},
        })
    df = pd.DataFrame(rows)
    df["league"] = [
        name_league.get(k) or club_league.get(norm_name(c)) or None
        for k, c in zip(df.key, df.club)
    ]
    # fill remaining gaps by majority league of the player's club-mates
    known = df[df.league.notna()]
    if len(known):
        club_mode = known.groupby("club").league.agg(lambda s: s.mode().iat[0])
        df["league"] = df.league.fillna(df.club.map(club_mode))
    df["league"] = df.league.fillna("Other league")
    unmapped = int((df.league == "Other league").sum())
    print(f"      {len(df):,} players · {df.club.nunique()} clubs · "
          f"{df.league.nunique() - 1} leagues named ({unmapped:,} unmapped)")
    return df


# ----------------------------------------------------------------------------
# 2. FBref observed performance
# ----------------------------------------------------------------------------
def load_fbref():
    print("[3/4] FBref Big-5 stats, seasons", SEASONS)
    import pyreadr
    frames = {}
    for st in STAT_TYPES:
        p = fetch(FBREF.format(st), f"fbref_{st}.rds")
        d = pyreadr.read_r(p)[None]
        d = d[d.Season_End_Year.isin(SEASONS)].copy()
        d["key"] = d.Player.map(norm_name)
        frames[st] = d
        print(f"      {st:11s} {len(d):>7,} player-seasons")

    std = frames["standard"]
    base = std.groupby(["key", "Season_End_Year"]).agg(
        name=("Player", "first"), club=("Squad", "first"), comp=("Comp", "first"),
        nation=("Nation", "first"), pos=("Pos", "first"), age=("Age", "first"),
        mins=("Min_Playing", "sum"), gls=("Gls", "sum"), ast=("Ast", "sum"),
        prgc=("PrgC_Progression", "sum"), prgp=("PrgP_Progression", "sum"),
        prgr=("PrgR_Progression", "sum"),
    ).reset_index()

    def merge(st, cols):
        d = frames[st]
        have = [c for c in cols if c in d.columns]
        if not have:
            return
        g = d.groupby(["key", "Season_End_Year"])[have].sum().reset_index()
        nonlocal base
        base = base.merge(g, on=["key", "Season_End_Year"], how="left")

    merge("shooting", ["Sh_Standard", "SoT_Standard", "npxG_Expected"])
    merge("passing", ["Cmp_Total", "Att_Total", "KP", "Final_Third",
                      "PPA", "xAG", "PrgDist_Total"])
    merge("defense", ["Tkl_Tackles", "TklW_Tackles", "Int", "Blocks_Blocks",
                      "Clr", "Err", "Tkl_percent_Challenges"])
    merge("possession", ["Att_Take", "Succ_Take", "CPA_Carries",
                         "Carries_Carries", "PrgDist_Carries"])
    merge("misc", ["Won_Aerial", "Lost_Aerial", "Recov"])

    base = base[base.mins.fillna(0) > 0].copy()
    print(f"      combined  {len(base):>7,} player-seasons "
          f"({base[base.Season_End_Year == LATEST].key.nunique():,} players in {LATEST})")
    return base


# ----------------------------------------------------------------------------
# 2b. Transfermarkt valuations, contracts and biography
# ----------------------------------------------------------------------------
def load_tm():
    """key -> [candidate dicts], from a published Transfermarkt dump."""
    print("[3b] Transfermarkt valuations & contracts")
    prof = pd.read_csv(fetch(TM_PROFILES, "tm_prof.csv"), low_memory=False)
    vals = pd.read_csv(fetch(TM_VALUES, "tm_val.csv"), low_memory=False)
    vals = vals[vals.value > 0][["player_id", "value", "date_unix"]]
    d = prof.merge(vals, on="player_id", how="left")

    dob = pd.to_datetime(d.date_of_birth, errors="coerce")
    # age is completed years, so floor — not round, which ages half the squad up
    d["tm_age"] = np.floor((SNAPSHOT - dob).dt.days / 365.25)
    d["cex"] = pd.to_datetime(d.contract_expires, errors="coerce").dt.year
    d["height_cm"] = pd.to_numeric(d.height, errors="coerce")   # already cm; 0 = unknown
    d.loc[(d.height_cm < 140) | (d.height_cm > 220), "height_cm"] = np.nan
    # names carry a "(id)" suffix in this dump; norm_name drops digits anyway
    d["key"] = d.player_name.map(norm_name)

    idx = {}
    d["joined_year"] = pd.to_datetime(d.joined, errors="coerce").dt.year
    for r in d[["key", "player_id", "current_club_name", "tm_age", "value", "cex",
                "height_cm", "foot", "citizenship", "main_position", "joined_year",
                "is_eu", "country_of_birth", "player_agent_name",
                "on_loan_from_club_name"]].to_dict("records"):
        if r["key"]:
            idx.setdefault(r["key"], []).append(r)
            # sources disagree on word order ("Son Heung-min" vs "Heung-Min Son"),
            # so always index a token-sorted alias to fall back on — including when
            # this record's own name is already in sorted order, which is exactly
            # the case the lookup needs to find.
            idx.setdefault("~" + " ".join(sorted(r["key"].split())), []).append(r)
    n_val = int(d.value.notna().sum())
    print(f"      {len(d):,} profiles · {n_val:,} with a market value · "
          f"{int(d.cex.notna().sum()):,} with a contract date")
    return idx


def match_tm(tm_idx, key, club, age):
    """Pick the Transfermarkt record most likely to be this player."""
    cands = tm_idx.get(key) or tm_idx.get("~" + " ".join(sorted(key.split())))
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    want = set(norm_name(club).split()) if isinstance(club, str) else set()
    best, best_s = None, -1
    for r in cands:
        s = 10 * len(want & set(norm_name(r["current_club_name"]).split()))
        if age and pd.notna(r["tm_age"]):
            s += max(0, 4 - abs(age - r["tm_age"]))
        if s > best_s:
            best, best_s = r, s
    return best


def load_global_career():
    """
    Appearances, injuries and valuation history for the whole world, keyed on the
    Transfermarkt player_id. FBref only covers the big 5, so this is what makes
    availability and momentum meaningful for a player in MLS or the Championship.
    Note these are match totals (minutes, goals, assists) — not event data, so
    they inform trajectory, never the attribute ratings.
    """
    print("[3c] global appearances, injuries & valuation history")
    # NOTE: this table's `minutes_played` column is NOT minutes — it is minutes
    # *per goal* (Haaland's 31 Premier League apps read "125" = 2790/22), and it
    # is null whenever a player did not score. Appearances, goals and assists are
    # sound, so workload is measured in appearances and minutes are ignored.
    perf = pd.read_csv(
        fetch(TM_PERF, "tm_perf.csv"),
        usecols=["player_id", "season_name", "nb_in_group", "nb_on_pitch",
                 "goals", "assists"],
        low_memory=False)
    perf = perf[perf.season_name.isin(TM_SEASONS)]
    for c in ["nb_in_group", "nb_on_pitch", "goals", "assists"]:
        perf[c] = pd.to_numeric(perf[c], errors="coerce").fillna(0)
    # one player can appear in several competitions per season; sum them
    agg = perf.groupby(["player_id", "season_name"]).sum(numeric_only=True).reset_index()

    cur = agg[agg.season_name == TM_LATEST].set_index("player_id")
    prior = (agg[agg.season_name != TM_LATEST]
             .groupby("player_id")[["nb_on_pitch", "nb_in_group", "goals", "assists"]].mean())

    career = {}
    for pid, r in cur.iterrows():
        pm = prior.loc[pid] if pid in prior.index else None
        apps, ga = float(r.nb_on_pitch), float(r.goals) + float(r.assists)
        squad = float(r.nb_in_group)
        papps = float(pm.nb_on_pitch) if pm is not None else apps
        pga = (float(pm.goals) + float(pm.assists)) if pm is not None else ga
        career[pid] = {
            "apps": int(apps), "squad": int(squad), "ga": int(ga),
            # share of matchday squads the player actually got on the pitch for
            "start_rate": round(apps / squad, 3) if squad > 0 else None,
            "app_trend": round(float(np.clip((apps - papps) / (papps + 8.0), -1, 1)), 3),
            "form_trend": round(float(np.clip((ga - pga) / (abs(pga) + 4.0), -1, 1)), 3),
            "inj_days": 0,
        }
    print(f"      {len(career):,} players with {TM_LATEST} appearances")

    inj = pd.read_csv(fetch(TM_INJURIES, "tm_inj.csv"), low_memory=False)
    inj = inj[inj.season_name.isin(TM_SEASONS)]
    inj["days_missed"] = pd.to_numeric(inj.days_missed, errors="coerce").fillna(0)
    hurt = inj.groupby("player_id").days_missed.sum()
    for pid, days in hurt.items():
        if pid in career:
            career[pid]["inj_days"] = int(days)
    print(f"      {int((hurt > 0).sum()):,} players with injury history in window")

    vh = pd.read_csv(fetch(TM_VALHIST, "tm_valhist.csv"), low_memory=False)
    vh = vh[vh.value > 0].copy()
    vh["d"] = pd.to_datetime(vh.date_unix, errors="coerce")
    vh = vh.dropna(subset=["d"]).sort_values("d")
    recent = vh[vh.d >= "2023-09-01"]
    first = recent.groupby("player_id").value.first()
    last = recent.groupby("player_id").value.last()
    trend = ((last - first) / first.replace(0, np.nan)).clip(-1, 3)
    for pid, t in trend.dropna().items():
        if pid in career:
            career[pid]["val_trend"] = round(float(t), 3)
    print(f"      {int(trend.notna().sum()):,} players with a 2-year valuation trend")
    return career


def load_transfers():
    """Career path: senior moves with fees, club count, and current loan status."""
    print("[3d] transfer history")
    t = pd.read_csv(fetch(TM_TRANSFERS, "tm_transfers.csv"),
                    usecols=["player_id", "transfer_date", "from_team_name",
                             "to_team_name", "transfer_type", "transfer_fee"],
                    low_memory=False)
    t = t[t.transfer_date.notna()]
    # youth-team steps ("West Ham U18 -> West Ham U23") are noise on a scouting
    # profile; keep moves between senior sides only
    youth = re.compile(r"\b(?:U\d{2}|Yth|Youth|Acad|B|II)\b", re.I)
    t = t[~t.to_team_name.astype(str).str.contains(youth, na=False)]
    t["fee_m"] = pd.to_numeric(t.transfer_fee, errors="coerce").fillna(0) / 1e6
    t = t.sort_values("transfer_date", ascending=False)

    out = {}
    for pid, g in t.groupby("player_id", sort=False):
        moves = []
        for r in g.head(3).itertuples(index=False):
            moves.append([str(r.transfer_date)[:7], str(r.from_team_name),
                          str(r.to_team_name), round(float(r.fee_m), 1),
                          str(r.transfer_type)])
        out[pid] = {
            "moves": moves,
            "clubs": int(g.to_team_name.nunique()),
            "top_fee": round(float(g.fee_m.max()), 1),
            "on_loan": bool(len(g) and str(g.iloc[0].transfer_type) == "Loan"),
        }
    print(f"      {len(out):,} players with a senior transfer record")
    return out


# ----------------------------------------------------------------------------
# 3. stats -> attributes (positional percentile + shrinkage)
# ----------------------------------------------------------------------------
def per90(num, mins):
    return np.where(mins > 0, num.fillna(0) * 90.0 / mins, 0.0)


def pct_rank(s, group):
    """Percentile within position group, scaled 0-100."""
    return s.groupby(group).rank(pct=True) * 100.0


def derive_from_stats(cur):
    """Build stat-derived attribute estimates for the latest season."""
    m = cur.mins.astype(float)
    fb_pos = cur.pos.fillna("").str.split(",").str[0]
    grp = fb_pos.map({"GK": "GK", "DF": "DEF", "MF": "MID", "FW": "ATT"}).fillna("MID")

    npxg = cur.get("npxG_Expected", pd.Series(0, index=cur.index)).fillna(0)
    sh = cur.get("Sh_Standard", pd.Series(0, index=cur.index)).fillna(0)
    est = pd.DataFrame(index=cur.index)

    # finishing: shot volume quality + finishing over expectation
    goals_np = (cur.gls.fillna(0) - 0)
    est["finishing"] = pct_rank(pd.Series(per90(npxg, m), index=cur.index)
                                + (goals_np - npxg).clip(-5, 5) * 0.05, grp)
    # creativity
    est["vision"] = pct_rank(pd.Series(per90(cur.get("xAG", 0), m), index=cur.index)
                             + pd.Series(per90(cur.get("KP", 0), m), index=cur.index) * 0.1, grp)
    # passing: completion% blended with progressive passing
    cmp_, att = cur.get("Cmp_Total", 0), cur.get("Att_Total", 0)
    comp_pct = pd.Series(np.where(pd.notna(att) & (att > 0), cmp_ / att * 100, np.nan),
                         index=cur.index)
    est["passing"] = pct_rank(comp_pct.fillna(comp_pct.median())
                              + pd.Series(per90(cur.prgp, m), index=cur.index), grp)
    # dribbling / carrying
    succ = cur.get("Succ_Take", 0)
    est["dribbling"] = pct_rank(pd.Series(per90(succ, m), index=cur.index)
                                + pd.Series(per90(cur.prgc, m), index=cur.index) * 0.3, grp)
    est["control"] = pct_rank(pd.Series(per90(cur.get("Carries_Carries", 0), m),
                                        index=cur.index), grp)
    # Defending. Raw action counts flatter busy defenders and punish elite CBs who
    # prevent situations from arising, so volume is only half the score; the other
    # half is duel-success rate, which rewards winning what you do contest.
    vol = (pd.Series(per90(cur.get("TklW_Tackles", 0), m), index=cur.index)
           + pd.Series(per90(cur.get("Int", 0), m), index=cur.index)
           + pd.Series(per90(cur.get("Clr", 0), m), index=cur.index) * 0.5
           + pd.Series(per90(cur.get("Blocks_Blocks", 0), m), index=cur.index) * 0.5)
    duel = cur.get("Tkl_percent_Challenges", pd.Series(np.nan, index=cur.index))
    duel = pd.Series(np.asarray(duel, dtype=float), index=cur.index)
    duel = duel.fillna(duel.median())
    errs = pd.Series(per90(cur.get("Err", 0), m), index=cur.index)
    est["defending"] = (pct_rank(vol, grp) * 0.5
                        + pct_rank(duel, grp) * 0.5
                        - pct_rank(errs, grp) * 0.05)
    # pressing proxy: ball recoveries
    est["pressing"] = pct_rank(pd.Series(per90(cur.get("Recov", 0), m), index=cur.index), grp)
    # aerial win rate
    won, lost = cur.get("Won_Aerial", 0), cur.get("Lost_Aerial", 0)
    tot = (won.fillna(0) + lost.fillna(0)) if hasattr(won, "fillna") else 0
    aer = pd.Series(np.where(np.asarray(tot) > 0, np.asarray(won.fillna(0)) /
                             np.maximum(np.asarray(tot), 1) * 100, np.nan), index=cur.index)
    est["aerial"] = pct_rank(aer.fillna(aer.median()), grp)
    # stamina proxy: minutes share
    est["stamina"] = pct_rank(m, grp)
    return est.clip(0, 100)


# ----------------------------------------------------------------------------
# 4. assemble
# ----------------------------------------------------------------------------
def main():
    priors = load_priors()
    fb = load_fbref()
    tm_idx = load_tm()
    career = load_global_career()
    transfers = load_transfers()

    # Latest complete season. Names collide across leagues (there are several
    # "Rodri"s), so keep every candidate and resolve per-player by club agreement
    # rather than silently taking whichever row sorted first.
    cur = (fb[fb.Season_End_Year == LATEST]
           .sort_values("mins", ascending=False)
           .reset_index(drop=True))
    est = derive_from_stats(cur)
    cand = cur.groupby("key").groups          # key -> row indices, minutes-desc


    # 3-season trends (real, observed)
    piv_min = fb.pivot_table(index="key", columns="Season_End_Year",
                             values="mins", aggfunc="sum")
    piv_ga = fb.assign(ga=fb.gls.fillna(0) + fb.ast.fillna(0)).pivot_table(
        index="key", columns="Season_End_Year", values="ga", aggfunc="sum")

    def trend(piv):
        cols = [c for c in SEASONS if c in piv.columns]
        if len(cols) < 2:
            return pd.Series(0.0, index=piv.index)
        last, prev = piv[cols[-1]].fillna(0), piv[cols[:-1]].mean(axis=1).fillna(0)
        return ((last - prev) / (prev.abs() + 300.0)).clip(-1, 1)

    min_trend, form_trend = trend(piv_min), trend(piv_ga)

    print("[4/4] matching priors to observed stats")
    out, matched = [], 0
    claimed = set()

    def fb_group(v):
        return {"GK": "GK", "DF": "DEF", "MF": "MID",
                "FW": "ATT"}.get(str(v or "").split(",")[0], "MID")

    def match_score(pr, i):
        """Evidence that prior row `pr` and FBref row `i` are the same person."""
        s = 10 * len(set(norm_name(pr["club"]).split())
                     & set(norm_name(cur.at[i, "club"]).split()))
        if LINE[pr["pos"]] == fb_group(cur.at[i, "pos"]):
            s += 3
        fa, pa = parse_age(cur.at[i, "age"]), pr["age24"]
        if fa and pa:
            s += max(0, 3 - abs((pa + AGE_OFFSET) - fa))
        return s

    def build(p, ci):
        c = cur.loc[ci] if ci is not None else None
        if p is not None:
            pos, name = p["pos"], p["name"]
            club, nation = p["club"], p["nation"]
            league, foot = p["league"], p["foot"]
            base_age = p["age24"]
            attrs = {k: float(p.get(f"a_{k}", 60) or 60) for k in ATTRS}
            overall_prior = p["overall"]
        else:  # FBref-only: a recent breakthrough EA FC 24 never listed
            fbp = str(c["pos"] or "").split(",")[0]
            pos = {"GK": "GK", "DF": "CB", "MF": "CM", "FW": "ST"}.get(fbp, "CM")
            name, club = c["name"], c["club"]
            nation = c["nation"] if isinstance(c["nation"], str) and c["nation"] else "—"
            league, foot, base_age = c["comp"], "Right", None
            attrs = {k: 60.0 for k in ATTRS}
            overall_prior = None

        mins = float(c["mins"]) if c is not None and pd.notna(c["mins"]) else 0.0
        conf, w = 0, 0.0
        if c is not None:
            w = mins / (mins + SHRINK_K)          # empirical-Bayes weight
            if p is None:
                w = max(w, 0.85)                  # no prior to fall back on
            e = est.loc[ci]
            for k in ATTRS:
                if k in e.index and pd.notna(e[k]):
                    attrs[k] = (1 - w) * attrs[k] + w * float(e[k])
            conf = 2 if mins >= 900 else 1
            club = c["club"] or club
            league = c["comp"] or league
            age = parse_age(c["age"]) or (base_age + AGE_OFFSET if base_age else None)
        else:
            age = base_age + AGE_OFFSET if base_age else None

        if pos == "GK" and p is not None and pd.notna(p["gk"]):
            attrs["positioning"] = float(p["gk"])

        tkey = c["key"] if c is not None else (p["key"] if p is not None else "")

        # Transfermarkt: valuation, contract, and better biography than either
        # of the game datasets carries.
        value = cexp = height = None
        gapps = gsquad = gga = ginj = 0
        gmt = gft = vtr = grate = None
        agent = birth = role = loan_from = None
        joined = None
        is_eu = None
        moves, nclubs, topfee, on_loan = [], None, None, False
        t = match_tm(tm_idx, tkey, club, age)
        if t:
            agent = t["player_agent_name"] if isinstance(t["player_agent_name"], str) else None
            birth = t["country_of_birth"] if isinstance(t["country_of_birth"], str) else None
            role = t["main_position"] if isinstance(t["main_position"], str) else None
            loan_from = (t["on_loan_from_club_name"]
                         if isinstance(t["on_loan_from_club_name"], str) else None)
            joined = int(t["joined_year"]) if pd.notna(t["joined_year"]) else None
            is_eu = bool(t["is_eu"]) if pd.notna(t["is_eu"]) else None
            tr = transfers.get(t["player_id"])
            if tr:
                moves, nclubs = tr["moves"], tr["clubs"]
                topfee = tr["top_fee"] if tr["top_fee"] > 0 else None
                on_loan = tr["on_loan"] or bool(loan_from)
            car = career.get(t["player_id"])
            if car:
                gapps, gsquad, gga = car["apps"], car["squad"], car["ga"]
                ginj = car["inj_days"]
                gmt, gft = car["app_trend"], car["form_trend"]
                grate = car["start_rate"]
                vtr = car.get("val_trend")
            if pd.notna(t["value"]):
                value = round(float(t["value"]) / 1e6, 2)      # EUR millions
            if pd.notna(t["cex"]):
                cexp = int(t["cex"])
            if pd.notna(t["height_cm"]):
                height = int(t["height_cm"])
            if isinstance(t["citizenship"], str) and t["citizenship"].strip():
                # dual nationals are stored as "Spain  Equatorial Guinea" (two
                # spaces, no comma); take the first, which is the primary listing
                nation = re.split(r"\s{2,}|,", t["citizenship"].strip())[0].strip()
            # FBref's age is already season-accurate; TM's DOB fills the rest
            if age is None and pd.notna(t["tm_age"]):
                age = int(t["tm_age"])
            # a baseline-tier club string is 2023/24; TM's is ~Sept 2025
            if not conf and isinstance(t["current_club_name"], str):
                club = t["current_club_name"]

        return {
            "n": name, "c": club, "l": league, "nat": nation,
            "p": pos, "pl": POS_LABEL[pos], "ln": LINE[pos],
            "ag": age, "ft": foot, "ht": height,
            "val": value, "cex": cexp,
            "mn": int(mins), "cf": conf,
            # global career: real for every league, not just the big 5
            "gap": gapps, "gsq": gsquad, "gga": gga, "inj": ginj,
            "grt": grate, "gmt": gmt, "gft": gft, "vtr": vtr,
            # profile depth
            "role": role, "agent": agent, "born": birth, "jn": joined,
            "eu": is_eu, "loan": loan_from, "onloan": on_loan,
            "car": moves, "ncl": nclubs, "tfee": topfee,
            "mt": round(float(min_trend.get(tkey, 0.0)), 3) if conf else 0.0,
            "ovr": int(overall_prior) if overall_prior and pd.notna(overall_prior) else None,
            "ft_": round(float(form_trend.get(tkey, 0.0)), 3) if conf else 0.0,
            **{k[:4]: int(round(min(100, max(1, attrs[k])))) for k in ATTRS},
        }

    # Greedy assignment, strongest priors first, each FBref row claimable once.
    # Players who share a name stay distinct people instead of collapsing.
    key_priors = priors.key.value_counts().to_dict()
    for p in priors.sort_values("overall", ascending=False,
                                na_position="last").to_dict("records"):
        free = [i for i in cand.get(p["key"], []) if i not in claimed]
        ci = None
        if free:
            best_s, best_i = max((match_score(p, i), i) for i in free)
            if best_s >= 2 or (len(free) == 1 and key_priors.get(p["key"], 1) == 1):
                ci, _ = best_i, claimed.add(best_i)
        if ci is not None:
            matched += 1
        out.append(build(p, ci))

    # FBref players with no EA FC 24 entry — recent breakthroughs worth scouting.
    for i in range(len(cur)):
        if i not in claimed and float(cur.at[i, "mins"] or 0) >= 450:
            matched += 1
            out.append(build(None, i))

    df = pd.DataFrame(out)
    df = df[df.ag.notna() & (df.ag >= 15) & (df.ag <= 45)]

    # League strength, derived from the data itself rather than a third-party
    # coefficient: the median squad valuation of each competition, percentile-
    # ranked. A 75-rated player in League Two is not a 75 in the Premier League,
    # and this is what lets the UI say so out loud.
    valued = df[df.val.notna() & (df.l != "Other league")]
    med = valued.groupby("l").val.median()
    counts = valued.groupby("l").val.size()
    med, counts = med[counts >= 20], counts[counts >= 20]
    if len(med):
        # Thinly-covered leagues only have their stars valued, which inflates the
        # median (Ukraine: 27 valued players vs Ligue 1's 400). Shrink each league
        # toward the global median in proportion to how little of it we can see.
        globe, K = float(valued.val.median()), 60.0
        shrunk = (counts * med + K * globe) / (counts + K)
        strength = (shrunk.rank(pct=True) * 100).round().astype(int)
        df["lgs"] = df.l.map(strength)
        top = strength.sort_values(ascending=False).head(6)
        print("      league strength (top 6): "
              + ", ".join(f"{k} {v}" for k, v in top.items()))
    else:
        df["lgs"] = None
    df = df.sort_values(["cf", "mn"], ascending=False).reset_index(drop=True)

    cols = list(df.columns)
    payload = {
        "meta": {
            "generated_for_season": LATEST,
            "seasons": SEASONS,
            "n_players": int(len(df)),
            "n_verified": int((df.cf == 2).sum()),
            "n_partial": int((df.cf == 1).sum()),
            "n_prior_only": int((df.cf == 0).sum()),
            "n_valued": int(df.val.notna().sum()),
            "n_contracts": int(df.cex.notna().sum()),
            "n_global_apps": int((df.gap > 0).sum()),
            "n_injury": int((df.inj > 0).sum()),
            "n_career": int(df.car.map(bool).sum()),
            "n_loan": int(df.onloan.sum()),
            "attrs": [k[:4] for k in ATTRS],
            "attr_labels": {k[:4]: k for k in ATTRS},
            "sources": {
                "priors": "EA FC 24 player ratings (global, 2023/24 vintage)",
                "stats": f"FBref Big-5 advanced season stats {SEASONS[0]}-{LATEST}",
                "leagues": "FIFA 22 dataset (club -> league mapping only)",
                "market": "Published Transfermarkt dump, values current to Sept 2025",
                "transfers": "Transfermarkt senior transfer history with fees",
                "career": "Transfermarkt appearances, injuries and valuation history, "
                          f"seasons {TM_SEASONS[0]}-{TM_LATEST}, all competitions",
            },
        },
        "cols": cols,
        # object dtype first: on a float column `where(..., None)` just re-inserts
        # NaN, and bare NaN is not valid JSON.
        "rows": df.astype(object).where(pd.notna(df), None).values.tolist(),
    }
    with open(OUT, "w") as f:
        json.dump(payload, f, separators=(",", ":"), allow_nan=False)

    mb = os.path.getsize(OUT) / 1e6
    print(f"\n  wrote {OUT}  ({mb:.1f} MB)")
    print(f"  {len(df):,} players | verified {payload['meta']['n_verified']:,} · "
          f"partial {payload['meta']['n_partial']:,} · "
          f"prior-only {payload['meta']['n_prior_only']:,}")
    print(f"  leagues: {df.l.nunique()} | clubs: {df.c.nunique()} | "
          f"stat-matched: {matched:,}")


if __name__ == "__main__":
    main()
