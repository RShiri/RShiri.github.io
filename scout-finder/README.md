# Scout Finder: data pipeline

Pick a player, see positional percentiles and the most similar players. This
folder is the data side only; the page comes next.

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
pip install pandas numpy requests        # + selenium if Understat blocks plain HTTP
python -m pipeline.build --xepl-csv ../../XEPL/epl_dashboard/database/player_match_stats.csv
python -m pipeline.build --understat EPL:2025-26 --understat LaLiga:2025-26
python -m pytest tests
```

The Understat fetcher has not been run against the live site yet (it was written
where Understat is unreachable). It tries the JSON endpoint, then the page blob,
then a real browser.
