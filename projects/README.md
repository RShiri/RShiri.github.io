# Vendored project copies

> Looking for the data? [`../DATA.md`](../DATA.md) maps every dataset in this repo —
> which directory holds the full match archive, what is in each database, and what
> lives only on the source repos.

Full working copies of the portfolio's project repositories, vendored here so the
whole portfolio — sites, scrapers, xG/xA model cores, and databases — sits in one
repo. Each directory is a snapshot of the source repo's default branch (no `.git`).

| Directory | Source repo | Snapshot commit | Date |
| --- | --- | --- | --- |
| `xepl/` | [RShiri/XEPL](https://github.com/RShiri/XEPL) | `7590105` | 2026-07-30 |
| `xlaliga/` | [RShiri/XLALIGA](https://github.com/RShiri/XLALIGA) | `d3e4ce8` | 2026-07-30 |
| `xworldcuptwit/` | [RShiri/XWORLDCUPTWIT](https://github.com/RShiri/XWORLDCUPTWIT) | `de25120` | 2026-07-30 |
| `f1visualized/` | [RShiri/F1Visualized](https://github.com/RShiri/F1Visualized) | `f916591` | 2026-07-06 |

Included everywhere: the dashboard sites (`*_dashboard/`, F1's `web/`), the full
`matches_detail` corpora the win-probability model trains on, the xG/xA model cores
(`xg_core/`, `xg_core_v3/` — coefficients, GBM trees, isotonic calibrators), the
processed databases (`*_dashboard/database/*.sqlite` + CSVs), scraper code, and
team logos.

Excluded (size only — GitHub Pages caps a published site at ~1 GB):

- `xworldcuptwit/WorldCup2026/` — rendered infographic PNG archive (~380 MB);
  the same renders live in the source repo.
- `xworldcuptwit/wc2026/matches/` — raw scrape cache (~220 MB); the derived
  `wc2026_dashboard/matches_detail/*.js` files here carry everything the models
  and dashboards consume.

The NBA dashboard is a Streamlit app (server-side); it cannot run as static
files, so its card on the portfolio page still links to the live deployment.

`live-pipeline/tradepipe/corpus.py` resolves these copies automatically (after
sibling clones and `/workspace` clones), so a fresh clone of this one repo can
refit the model end-to-end: `python3 live-pipeline/tradepipe/calibrate.py`.

## These copies have moved ahead of their source repos

The vendored dashboards are no longer byte-identical to the snapshots above. Two
deliberate changes were made here, and the source repos still have the old code:

- **`winprob_params.js`** regenerated as **v3** (the retuned win-probability model —
  see `live-pipeline/README.md` for the holdout numbers).
- **`winprob_model.js`** added, and each dashboard's `match.js` now delegates its
  win-probability maths to it. The three dashboards had drifted into three separate
  implementations of the same model; there is now one, generated from
  `live-pipeline/web/winprob_model.js` and verified against the Python model to 5e-16.
  `match.html` gained the matching `<script>` tag.

`calibrate.py` writes both files into every dashboard it can find — the corpus root it
read from **and** these vendored copies — so a refit keeps them in step. To push the
improvements back upstream, copy each `*_dashboard/` change into the corresponding
source repo.

To refresh a snapshot: re-clone the source repo, re-copy over the directory with
the same exclusions, re-apply the two changes above (or just re-run `calibrate.py`
and re-patch `match.js`/`match.html`), and update the commit column.
