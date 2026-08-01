# F1Visualized — Latest Race Pipeline

An automated, end-to-end Python pipeline that scrapes Formula 1 timing data for
the **most recently completed Grand Prix** and renders broadcast-style MP4
animations of the race.

---

## What it produces

Two 1280×720 H.264 videos, both driven from one scrape of the lap-by-lap
position log:

### 1. `latest_race_replay.mp4` — the position-battle race *(headline)*

Every driver is a little **car**. All cars sit on the **same vertical line** (the
current lap) and slide up and down between the position lanes (P1→P20) as the
running order changes — you watch them overtake each other — while the field
sweeps left→right toward the finish line as the laps tick by.

| Element | Encoding |
|---|---|
| **Running order** | y-axis lanes, P1 top → P20 bottom; cars swap lanes on every position change |
| **Race progress** | the line of cars sweeps left→right across the lap axis to the FINISH |
| **Driver identity** | team-coloured car sprite + 3-letter code |
| **Tyre compound** | colour + letter chip — Red `S`, Yellow `M`, White `H`, Green `I`, Blue `W` |
| **Pit stop** | green `P` chip + green car outline on the lap a driver pits |
| **Virtual Safety Car** | flashing yellow `VIRTUAL SAFETY CAR` banner while a VSC is deployed |
| **Retirement** | the car freezes and dims at the lap of retirement |

### 2. `latest_race_timelapse.mp4` — the position-by-lap timeline

The same race as a classic bump chart: each driver's team-coloured trace grows
left→right, crossing as positions change, with the abbreviation + tyre badge at
the head of the line (VSC banner, `[IN PIT]` tags and dimmed retirements too).

---

## Season dashboard — 2025 / 2026

A static, responsive web dashboard for the **2025 and 2026 seasons**, deployable
to GitHub Pages. A **season toggle** switches between years across four sections:

* **Overview** — championship leaders, next-race countdown, last-race podium, top-5 tables.
* **Standings** — full drivers' & constructors' championships with team-coloured points bars.
* **Calendar** — every round with country flags, completed winners and a "Next Up" highlight.
* **Results** — per-race classification, podium, fastest lap, an **interactive
  lap scrubber** (a position bump-chart you drag or play through lap-by-lap —
  real telemetry when present, otherwise an honest *grid → finish (approx)*
  progression from each driver's real grid, finish and laps completed), and an
  embedded **race-replay video** when one exists for that round.

The replay video is optional: the video workflow publishes each rendered race to
`web/media/<year>-<round>.mp4`, and the Results tab embeds it if present (hidden
gracefully otherwise).

```
web/                     The dashboard (static HTML/CSS/JS — no framework)
  index.html
  assets/styles.css      Dark F1 theme, responsive
  assets/app.js          Season toggle, tabs, rendering (fetch or embedded data)
  data/2025.json         Season data (schedule + results + standings)
  data/2026.json
fetch_season.py          Fetches real data -> web/data/*.json
.github/workflows/deploy_dashboard.yml   Build data + deploy to GitHub Pages
```

**Real data.** `fetch_season.py` builds each season from two public sources that
need no API key: the **calendar** from `fastf1.get_event_schedule`, and
**results + standings** from the open-source [**f1db**](https://github.com/f1db/f1db)
dataset (read straight from its committed source YAML on
`raw.githubusercontent.com`, authoritative and updated through the live 2026
season). The committed `web/data/*.json` is therefore the **real** classification
— e.g. the 2025 champion is Lando Norris (423), and the 2026 table is live.

Build the data and preview locally:

```bash
python fetch_season.py                  # both seasons -> web/data/{2025,2026}.json
cd web && python -m http.server         # open http://localhost:8000
```

To publish: enable **GitHub Pages → Source: GitHub Actions**, then run the
**Deploy F1 Dashboard** workflow — it refreshes the data and deploys `web/`.

> A note on the 2026 calendar: `fastf1`'s pre-season schedule can differ from
> f1db's live one for a round or two. A scheduled race with no result yet is
> shown as **TBC** rather than invented.

The dashboard consumes a small JSON contract, so the data producer
(`assemble_season`) is decoupled and unit-tested.

---

## Race animations

The pipeline is deliberately split into small, importable pieces so it can be
scripted, tested offline, or reused by the dashboard without rewriting core logic.

```
config.py          Shared style tokens, palettes, the car sprite and file paths
scraper.py         Stage 1 — dynamic data extraction & tidy transformation  → data/
race_animator.py   Stage 2 — position-battle race (cars) engine  → latest_race_replay.mp4
animator.py        Stage 2 — position-by-lap timeline engine      → latest_race_timelapse.mp4
combine_gp_videos.py  Stitch both panels into one synced video    → latest_race_combined.mp4
tests/             Network-free unit tests for the pure data transforms
.github/workflows/f1_latest_video.yml   Stage 3 — on-demand CI/CD
```

`combine_gp_videos.py` renders both engines with a **matched** `fps` /
`frames_per_lap` — so lap *N* lands on the same frame in both — then ffmpeg
places them side by side (or `--layout stack`), yielding one in-sync
comparison video per Grand Prix:

```bash
python combine_gp_videos.py                 # side-by-side -> latest_race_combined.mp4
python combine_gp_videos.py --layout stack  # timeline under the race
```

### Stage 1 — `scraper.py`

* Finds the latest completed race **dynamically** — no hard-coded round. It
  walks the event schedule backwards from today and loads the first race whose
  timing data is actually published, so it self-heals in the window right after
  a race when data isn't live yet.
* Extracts, per driver per lap: **lap number, position, tyre compound**, an
  `is_pit_stop` flag (set on the lap a driver enters the pit lane), and an
  `is_vsc` flag.
* Identifies **Virtual Safety Car** laps from the race-control message feed
  (with a `TrackStatus` fallback).
* Emits a tidy `data/race_data.csv` plus `data/race_meta.json` (event details,
  total laps, per-driver name/team/colour, VSC laps).

The heavy lifting lives in **pure functions** (`build_laps_dataframe`,
`extract_vsc_laps`, `build_driver_meta`, …) that take plain DataFrames, so they
are trivially unit-testable and reusable.

### Stage 2 — `race_animator.py` and `animator.py`

Two `matplotlib.animation.FuncAnimation` engines, both fed by the Stage 1
position log (no telemetry needed):

* **`race_animator.py`** — the position-battle race. Draws every driver as a car
  sprite (`config.car_marker()`), all on the current-lap line, and slides them
  between position lanes as the order changes.
* **`animator.py`** — the position-by-lap bump-chart timeline.

Both use sub-lap interpolation for smooth motion, and a system `ffmpeg` when
available, transparently falling back to the `imageio-ffmpeg` binary otherwise.

### Stage 3 — `.github/workflows/f1_latest_video.yml`

On-demand (`workflow_dispatch`) CI that installs Python 3.11 + ffmpeg, runs the
scrape + both renders, and uploads the videos as a workflow artifact.

---

## Local usage

```bash
pip install -r requirements.txt

# Stage 1 — scrape the most recent completed race (or a specific one)
python scraper.py                       # latest completed GP
python scraper.py --year 2024 --round 11  # a specific historical race

# Stage 2 — render the videos
python race_animator.py                 # -> latest_race_replay.mp4  (cars)
python animator.py                      # -> latest_race_timelapse.mp4  (timeline)

# Tweak the look
python race_animator.py --fps 30 --frames-per-lap 8 --width 1920 --height 1080
```

Run the offline tests with `pytest -q`.

---

## CI/CD — running it on GitHub

1. Open the **Actions** tab → **F1 Latest Race Timelapse** → **Run workflow**.
2. Optionally set `year` / `round` (blank = latest completed race).
3. When it finishes, download the `latest_race_timelapse` artifact.

**Triggers.** The workflow is `workflow_dispatch` only — manual, on-demand. It is
structured so a scheduled `cron` trigger can be added later by dropping a
`schedule:` block into the `on:` section; no Python changes required.

**Authentication (PAT).** Checkout and the optional commit step authenticate
with a Personal Access Token. Create a repo secret named **`F1VIZ_PAT`** (a
fine-grained PAT with `contents: write`); the workflow falls back to the default
`GITHUB_TOKEN` if it is not set. To also commit the generated video + data back
to the repo, tick the **`commit_output`** input when dispatching.

---

## Extending toward a live dashboard

The modular design leaves clean seams for future work:

* **Historical back-fill / batch** — every function already accepts explicit
  `year` / `round_number`; loop over a season to build an archive.
* **Live dashboard** — a Streamlit/Dash front-end can import
  `scraper.process_session(...)` for the same tidy DataFrame, and reuse the
  palettes and tyre/compound styles in `config.py` for consistent styling.
* **Scheduled automation** — add a `schedule:` cron block to the workflow to run
  automatically after each race.

---

## Notes

* `fastf1` caches downloads under `.fastf1_cache/` (git-ignored) so re-runs are
  fast.
* Rich lap/telemetry data is available from the **2018** season onward, which is
  how far back the "latest completed race" search will look.
