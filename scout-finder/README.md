# Scout Finder

Pick a player, see positional percentiles and the most similar players.
`index.html` is the page (served at rshiri.github.io/scout-finder/): search,
percentile bars and radar, similar players, a numbers-only scouting note and a
position/league finder. It reads `data/universe_2025-26.json`; everything below
is the pipeline that builds that file. The upgrade plan is in [PLAN.md](PLAN.md),
progress and mistakes in [PROGRESS.md](PROGRESS.md).

## Universe

12 leagues (`pipeline/leagues.py`): the big five; Portugal, Netherlands, Belgium,
the Championship, Brazil and Argentina as feeder leagues; and Israel's Ligat ha'Al.

Each player gets two percentiles per metric: within the same position in his
own league (`pct_league`), and across the whole universe after a league-strength
adjustment (`pct`, see `pipeline/league_strength.py`). Similar-player search runs
across the whole universe, so it can suggest a Belgian league winger for a
Premier League one.

A stat a league does not publish (xG in smaller leagues) stays empty, never 0.
FotMob itself leaves a stat out of a player's match when it is zero (no xG key
for a player who never shot), so within a match a stat anyone has is 0 for the
rest; only a stat nobody in the match has stays empty. In 2025-26 that is xG,
npxG and xA in Ligat ha'Al; every other league has them.

Positions come from the starting slot (FotMob positionId, mapped in
`fetch_fotmob.POSITION_ID`); a player's group is his most-started slot. Bench
appearances only count for players who never started. FotMob's slots do not
separate a holding midfielder from a box-to-box one (a 4-3-3's anchor sits level
with the 8s, a 4-2-3-1's pivot pair are often 8s), so every central midfielder
is CM and the FotMob universe has seven groups, no DM. A player who changed
leagues mid-season gets one entry per league (`fotmob:<id>@<league>`).

League strength: the ClubElo API was down when `data/universe_2025-26.json` was
built (Oct 2026), so the factors come from the league averages on the clubelo.com
front page that day (2026-27 membership), Brazil and Argentina included.

## Sources

FBref lost its Opta advanced stats (xG, xA, progressive actions) in January 2026,
so the pipeline uses two free sources instead.

| Source | Season | What it adds | How we get it |
|---|---|---|---|
| FotMob | 2025-26 and 2026-27 (EPL) | xG, xA, shots, passes, key passes, take-ons, tackles, interceptions, clearances, aerials | XEPL's `player_match_stats.csv`, which XEPL already scrapes from FotMob after every matchday. Summed to season totals here. |
| Understat | 2025-26 (top 5 leagues) | npxG, xGChain, xGBuildup | One request per league-season (`pipeline/sources/understat.py`) |

Neither source publishes progressive passes or carries. xGBuildup (Understat) is
the closest free stand-in: the xG of possessions a player helped build, without
the shot or the assist.

## Flow

```
source adapter -> one row per player-season (schema.py)
              -> per-90 rates (and pass %, xG per shot)
              -> percentiles within position group (8 groups, positions.py)
              -> similar players: cosine similarity on z-scored rates, same group
              -> data/<source>_<league>_<season>.json
```

Minutes floor: 900 for a finished season. Early in a season it drops to 30% of
the most-played player's minutes, so the current season is usable from about
matchday 4.

## Run

```
pip install -r requirements.txt          # + selenium if Understat blocks plain HTTP
python -m pipeline.fetch_fotmob --check                 # FotMob's name for each league id
python -m pipeline.fetch_fotmob --all --season 2025-26  # resumable; caches every match
python -m pipeline.build --fotmob --elo-date 2026-05-31
python -m pipeline.build --xepl-csv ../../XEPL/epl_dashboard/database/player_match_stats.csv
python -m pipeline.build --understat EPL:2025-26 --understat LaLiga:2025-26
python -m pytest tests
```

The Understat fetcher has not been run against the live site yet (it was written
where Understat is unreachable). It tries the JSON endpoint, then the page blob,
then a real browser.
