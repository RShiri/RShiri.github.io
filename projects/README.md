# Vendored project copies

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

To refresh a snapshot: re-clone the source repo, re-copy over the directory with
the same exclusions, and update the commit column above.
