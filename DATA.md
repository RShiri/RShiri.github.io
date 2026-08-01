# Where the data lives

One map of every dataset in this repo: what it is, how big, and which one is
the source of truth. Measured, not estimated — re-run the commands at the
bottom to refresh.

## TL;DR

- **The full match archive is `projects/*/[dashboard]/matches_detail/` — 3,272 matches, 82,310 shots, ~650 MB across five directories.** That is the database everything else is derived from.
- **The biggest single one is `projects/xepl/epl_dashboard/matches_detail/` — 1,520 matches, 305 MB.**
- **The `.sqlite` files are NOT the archive.** Each holds only the *current* season (380 EPL matches, 380 La Liga, 104 WC2026). Opening `epl.sqlite` looking for four seasons will find one.

## 1. Match event corpora — the real database

One `window.MATCH_DETAIL = {...}` JS file per match: shots (x, y, xG, body,
situation, on-target, blocked), goals, lineups with per-player stats, and
`maxMin`. Every model on this site is trained on these.

| Corpus | Path | Matches | Size |
| --- | --- | --- | --- |
| EPL 2022-23 → 2025-26 | `projects/xepl/epl_dashboard/matches_detail/` | 1,520 | 305 MB |
| La Liga 2022-23 → 2025-26 | `projects/xlaliga/laliga_dashboard/matches_detail/` | 1,520 | 295 MB |
| World Cup 2026 | `projects/xworldcuptwit/wc2026_dashboard/matches_detail/` | 107 files → 104 | 23 MB |
| World Cup 2018 | `projects/xworldcuptwit/wc2026_dashboard/editions/2018/matches_detail/` | 64 | 13 MB |
| World Cup 2022 | `projects/xworldcuptwit/wc2026_dashboard/editions/2022/matches_detail/` | 64 | 14 MB |
| **total** | | **3,272** (after dedup) | **~650 MB** |

WC2026 ships 107 files for 104 matches: three knockout fixtures were scraped
twice, once under a placeholder id (`Winner_QF_3_vs_...`) and once under the
real one. `corpus.py` dedupes them by `(date, home, away)`, preferring the
real id.

**Loader:** `live-pipeline/tradepipe/corpus.py` resolves all five, in this
order — sibling clones (`../XEPL`), `/workspace/<name>`, then the vendored
`projects/<name>`. So a fresh clone of this repo alone can refit the model.

## 2. Per-season databases — current season only

Derived aggregates the dashboards read. Useful, but **one season each**:

| File | Matches | Other tables | Size |
| --- | --- | --- | --- |
| `projects/xepl/epl_dashboard/database/epl.sqlite` | 380 | 11,492 player-match rows, 537 players, 760 team-match, standings | 1.6 MB |
| `projects/xlaliga/laliga_dashboard/database/laliga.sqlite` | 380 | 11,953 player-match, 600 players | 1.5 MB |
| `projects/xworldcuptwit/wc2026_dashboard/database/wc2026.sqlite` | 104 | 3,286 player-match, 1,039 players | 704 KB |
| `.../editions/2018/database/wc2018.sqlite` | 64 | 1,788 player-match | 392 KB |
| `.../editions/2022/database/wc2022.sqlite` | 64 | 1,995 player-match | 428 KB |

Each sits beside CSV exports of the same tables (`*_match_stats.csv`,
`players.csv`, `standings.csv`, `results.csv`).

## 3. Models

| Artifact | Path | Notes |
| --- | --- | --- |
| xG / xA runtime (v3) | `projects/<repo>/xg_core_v3/` | 23-feature LR + GBM + market distill, isotonic calibrator, per-league shifts, `penalty_xg = 0.794`. **`xg_artifact.json` is byte-identical in all three repos** (trained 2026-07-07) — one model, three copies. |
| xG runtime (v1) | `projects/<repo>/xg_core/` | Superseded by v3; kept for the training scripts. |
| Win probability | `assets/data/winprob/model_params.json` | v3, fit on all 3,272 matches. Single source of truth; `calibrate.py` ships derived copies into each dashboard as `winprob_params.js`. |

⚠️ The three `xg_core_v3/` **code** copies have drifted even though the model
artifact has not — see "Known issues" below.

## 4. Derived site data (small, regenerable)

| Path | What | Rebuild with |
| --- | --- | --- |
| `assets/data/argentina/` | 8 Argentina WC2026 matches for the match centre | `assets/data/build_argentina.py` |
| `assets/data/winprob/` | Per-minute win-prob timelines + fitted params | `tradepipe/calibrate.py`, then `build_timelines.py` |
| `assets/data/pipeline/` | The real TRADE360 message envelopes for the browser console | `tradepipe/dump_feed.py` |
| `projects/*/[dashboard]/player_lab/` | Per-team player pages (68 MB EPL, 16 MB La Liga, 4.5 MB WC) | the dashboards' `build_player_lab.py` |

## 5. Not in this repo

| Data | Size | Where it is |
| --- | --- | --- |
| Raw WhoScored match blobs (EPL, La Liga) | large | Your machine only — gitignored (`epl/matches/20*/*.json`). **These are the only copy, and the only place shot-level card minutes exist.** |
| WC2026 raw scrapes | 218 MB | `RShiri/XWORLDCUPTWIT` only (excluded here for size) |
| WC2026 rendered PNG archive | 381 MB | `RShiri/XWORLDCUPTWIT` only |

## Size budget

810 MB working tree + 161 MB git history ≈ **971 MB**. GitHub Pages publishes
the working tree and caps a site at **1 GB**, so there is ~190 MB of headroom —
roughly one more scraped season of EPL + La Liga. Before the season after that,
move historical seasons to Release assets or trim `player_lab` (88 MB total,
fully regenerable).

## Known issues

- **`xg_core_v3` code has drifted across the three repos while the model artifact has not.** XEPL and XLALIGA each independently added a collision-safe scorer (`match_xg_by_id` / `match_xg_by_event`, keyed by `id(event)`) because *WhoScored `eventId` is not unique within a match* — XLALIGA's own comment records that in ~15% of its matches two shots share one, so a `{eventId: xG}` dict silently mis-assigns them. **XWORLDCUPTWIT still builds exactly that dict** (`wc2026_dashboard/xg_model.py`, `wc2026/renderer.py`), so some World Cup shots may carry another shot's xG. The impact cannot be measured from the published files — it needs the raw blobs, which are local-only. Fix by porting XEPL's `match_xg_by_id` and re-running the WC build.
- The vendored dashboards have moved ahead of their source repos (v3 win-prob params + shared `winprob_model.js`); see `projects/README.md`.

## Re-measuring

```sh
# corpus sizes and match counts
for d in projects/*/[a-z]*_dashboard/matches_detail \
         projects/xworldcuptwit/wc2026_dashboard/editions/*/matches_detail; do
  echo "$(ls $d/*.js | grep -vc _index) $(du -sh $d | cut -f1) $d"
done

# sqlite row counts
find projects -name '*.sqlite' -exec sh -c \
  'echo "$1"; sqlite3 "$1" "select name from sqlite_master where type=\"table\";"' _ {} \;

# total footprint
du -sh --exclude=.git . && du -sh .git
```
