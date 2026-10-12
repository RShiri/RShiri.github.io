# Scout Finder: data pipeline

Pick a player, see positional percentiles and the most similar players. This
folder is the data side only; the page comes next.

## Universe

12 leagues (`pipeline/leagues.py`): the big five; Portugal, Netherlands, Belgium,
the Championship, Brazil and Argentina as feeder leagues; and Israel's Ligat ha'Al.

Each player gets two percentiles per metric: within the same position in his
own league (`pct_league`), and across the whole universe after a league-strength
adjustment (`pct`, see `pipeline/league_strength.py`). Similar-player search runs
across the whole universe, so it can suggest a Belgian league winger for a
Premier League one.

A stat a league does not publish (xG in smaller leagues) stays empty, never 0.

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
