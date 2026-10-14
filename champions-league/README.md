# Champions League dashboard

Static page (`index.html`) over one data file (`data/ucl.json`). Five seasons, two formats:

| Seasons | Format | First phase | Knockouts |
|---|---|---|---|
| 2022-23, 2023-24 | 32 clubs, 8 groups of 4 | 6 games, top 2 through, 3rd to Europa League | R16, QF, SF, final |
| 2024-25 onward | 36 clubs, one league table | 8 games; 1-8 to R16, 9-24 to a knockout playoff, 25-36 out | playoff, R16, QF, SF, final |

## Data

- `data/raw/cl_<season>.txt`: [openfootball/champions-league](https://github.com/openfootball/champions-league) (CC0), copied from commit `abfaedd` (July 2026). Complete through the 2025-26 final.
- `data/raw/cl_2026-27.csv`: the current season, entered by hand from news reports because openfootball has not published it yet. Blank scores are matches not played or not entered yet.

## Refresh

```
python champions-league/pipeline/build_data.py
```

No packages needed. To update the current season, add rows or scores to `cl_2026-27.csv` and rebuild. When openfootball publishes `2026-27/cl.txt`, copy it to `data/raw/cl_2026-27.txt`; the `.txt` wins over the `.csv`.

Nothing here needs FotMob, so it runs from anywhere. FotMob (blocked from the cloud) would be the route for an automatic weekly refresh run on Ram's PC.
