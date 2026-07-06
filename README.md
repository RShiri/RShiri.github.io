# rshiri.github.io - Ram Shiri's portfolio

A single-page personal portfolio (data science in sports). Static HTML/CSS/JS - no build step,
no dependencies. Published with **GitHub Pages** at <https://rshiri.github.io/>.

## Files
| File | Purpose |
| --- | --- |
| `index.html` | The whole page (nav, hero, about, live analytics, projects, contact) |
| `styles.css` | Base brand - Space Grotesk + Inter, indigo→cyan accent |
| `main.js` | Nav, scrollspy, theme toggle, the interactive shot / take-on maps, the Argentina match centre (picker, stat bars, shot map, goal replays), and the F1 lap-by-lap race-progression chart |
| `sample.html` | Redesign preview (loads `styles.css` + `sample.css`, `noindex`) - "player card" hero, richer project cards |
| `sample.css` | Overrides layered on top of `styles.css` for the `sample.html` redesign |
| `assets/` | Favicon, CV PDF, project screenshots, OG image |
| `assets/data/*.json` | Chart data: `yamal_shots` / `yamal_takeons` (shot & take-on maps), `f1_race_progression` (F1 bump chart), `arg_alg_match` (single-match fallback for the match centre) |
| `assets/data/argentina/` | One JSON per Argentina WC2026 match (+ `index.json` manifest) driving the match-centre picker |
| `assets/data/build_argentina.py` | Regenerates `assets/data/argentina/*` from the sibling **XWORLDCUPTWIT** event pipeline (ports the dashboard's goal-sequence reconstruction). Run `python3 assets/data/build_argentina.py` after new Argentina games are scraped |

## Before you go live - 3 quick edits
1. **LinkedIn** - open `main.js` and set `LINKEDIN_URL` to your profile URL; the LinkedIn
   link stays inactive until you do.
2. **CV** - replace `assets/Ram_Shiri_CV.pdf` with your real CV (keep the filename).
3. **Screenshots** - the images in `assets/img/` (`bcn.png`, `nba.png`, `wc2026.png`,
   `f1.png`, `xepl.png`) can be re-captured any time; if an image is missing the card
   shows a styled gradient fallback.

## Run locally
Any static server works, e.g.:
```
python -m http.server 8000
```
then open <http://localhost:8000>.

## Deploy
This repo is a **GitHub user site** (`rshiri.github.io`), so GitHub Pages serves the `main`
branch root automatically - just push. No Actions workflow or `gh-pages` branch needed.
