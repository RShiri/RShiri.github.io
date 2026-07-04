# Prompt - xLaLiga & xEPL (league-scale xG)

A self-contained brief for building two **league-wide expected-goals (xG)
products** on this site:

- **xLaLiga** - xG for every team & player in La Liga (2025/26).
- **xEPL** - the same for the English Premier League (2025/26).

Both share one engine. It is the Lamine Yamal shot map generalised from a
single player's 152 shots to a whole league's ~9,000+ shots, with two additions
that turn "a shot map" into "an xG product": **colour-by-team** and an **xG
league table** (who is over/under-performing their chances). The hallmark
mechanic - the **kicked-ball direction** onto the goal mouth - is carried over
unchanged, because that is the piece that makes the shot paths read as
direction instead of a starburst on the goal centre.

> Single-player instance and shared implementation anchors:
> `docs/lamine-yamal-xg-map.prompt.md`, `main.js` (`goalEndX`, `makePath`,
> `makeDot`), `index.html` (`#shotmap`), `styles.css` (`.shot`, `.shot-path`).

---

## The prompt (shared spec, parameterised by `LEAGUE`)

> Build a dependency-free, interactive **league xG product** rendered as inline
> SVG + plain DOM (no chart library, no framework). It has two linked views
> sharing one dataset:
>
> 1. an **xG league table** (teams ranked by xG, actual vs expected), and
> 2. a **filterable shot map** (every shot in the league, drawn on a half-pitch
>    with xG-sized markers and paths onto the goal mouth).
>
> The page must be fully readable with JS off; both views are progressive
> enhancements. Everything is parameterised by a single `LEAGUE` config
> (name, slug, team list + colours, data files) so the exact same code renders
> **xLaLiga** or **xEPL** by swapping that config (see **League configs**).
>
> ### Data
> Load two JSON feeds per league from `assets/data/{LEAGUE.slug}/`:
>
> **`shots.json`** - array of every shot in the season. Each shot extends the
> single-player schema with `team` / `opp` / `player`:
>
> ```json
> { "team": "Barcelona", "opp": "Real Oviedo", "player": "Lamine Yamal",
>   "x": 383.5, "y": 154.9, "xg": 0.095, "min": 72, "md": 8,
>   "out": "goal", "body": "Left foot", "situ": "Open play", "gy": 53 }
> ```
>
> - `team` - shooting team; `opp` - defending team; `player` - shooter.
> - `x`, `y` - shot **origin** in the SVG's coordinate space (goal at the
>   **top**; larger `y` = further from goal).
> - `xg` in `[0,1]`; `min` match minute; `md` matchday/round.
> - `out` - `goal | saved (on target) | off (off target) | blocked`.
> - `body` (`Left foot|Right foot|Header`), `situ` (`Open play`, `Penalty`,
>   `Fast break`, `Corner`, `Free kick`, ...).
> - `gy` - **optional** WhoScored `goalMouthY` (0-100): where the ball crossed
>   the line. `50` = centre, `~45/55` = posts. Ground truth for direction when
>   present; otherwise derive it (see **Kicked-ball direction**).
>
> **`results.json`** - one row per played match (drives the actual-vs-xG
> columns the shots alone can't give you): `{ "md", "home", "away", "hg",
> "ag" }` (home/away goals). Points and goal difference are derived from this.
>
> Fall back to a small hard-coded sample per feed if a fetch fails; the page
> must never blank out.
>
> ### xG league table (the "x{League}" headline)
> Aggregate `shots.json` + `results.json` per team into a sortable table:
>
> - **xGF** = sum of `xg` where `team === T` (chances created).
> - **xGA** = sum of `xg` where `opp === T` (chances conceded).
> - **xGD** = xGF - xGA.
> - **GF / GA / Pts** from `results.json` (win 3, draw 1).
> - **xPts** - expected points: simulate each match outcome from the two teams'
>   per-shot xG (or a simpler Poisson on match xG totals) and sum expected
>   points. Show **Pts - xPts** as the over/under-performance column, coloured
>   green (over) / red (under).
> - Default sort by xGD desc; every column is click-to-sort. Row click filters
>   the shot map to that team.
>
> This table is what distinguishes xLaLiga / xEPL from a plain shot map: it
> ranks the league by chance quality and flags who is riding or wasting xG.
>
> ### Pitch geometry (attacking half, goal on top - unchanged)
> - SVG `viewBox="0 0 680 520"`; attacking half, goal line across the **top**.
> - `GOAL_X = 340` (goal-mouth centre = horizontal centre), `GOAL_Y = 30`
>   (goal line), posts at `x = 308 / 372` (64px goal), `GOAL_SCALE = 6.4` px per
>   `goalMouthY` unit so `x = GOAL_X + (gy - 50) * GOAL_SCALE` puts `gy 45/55`
>   on the posts.
> - Box, six-yard box, penalty arc, centre-circle arc as faint white strokes on
>   a dark navy pitch; goal bar on the line; penalty spot dot.
> - Ordered groups `#pathLayer` (paths, underneath) then `#shotLayer` (markers).
>   Within each, draw non-goals first and **goals last** so goals read on top.
>
> ### Kicked-ball direction (the shot path) - carried over verbatim
> Every shot draws a straight path from its origin `(x, y)` to a point on the
> goal line. **Never send every path to the goal centre** - a constant endpoint
> collapses all paths onto one pixel and the map becomes a starburst where even
> misses look aimed dead centre. Compute a distinct endpoint per shot:
>
> 1. **Measured data wins.** If the shot has numeric `gy`, end at the real
>    crossing point: `endX = GOAL_X + (gy - 50) * GOAL_SCALE`, `endY = GOAL_Y`.
>    This always overrides the fallback.
>
> 2. **No `gy` -> a stable, outcome-aware fan across the goal mouth.** Give each
>    shot **deterministic** jitter (hash of `x`, `y`, `min` -> `[0,1)`, e.g.
>    `frac(sin(x*12.9898 + y*78.233 + min*37.719) * 43758.5453)`). Deterministic
>    matters: the fan must be stable across re-renders and re-filters, never
>    `Math.random()`. With `jit = hash - 0.5`:
>    - **Off target (`off`):** end **wide of a post**, on the shot's side.
>      `side = x >= GOAL_X ? +1 : -1; endX = GOAL_X + side*(42 + |jit|*26)`.
>    - **On target / blocked:** lean toward the shooter's side and fill the
>      mouth: `lean = (x - GOAL_X)/40;
>      endX = clamp(GOAL_X + lean + jit*50, 311, 369)` (just inside the posts).
>    - **Blocked (`blocked`):** shorten the whole path to **60%**
>      (`ex = x + (ex - x)*0.6`, `ey = y + (ey - y)*0.6`) so it dies en route.
>
> Paths then radiate across the whole goal mouth, misses splay outside the
> posts, blocks stop partway, and any shot with a real `gy` snaps exactly to
> where the ball went. Adding a `gy` later corrects that one shot with no other
> change. (At league scale you draw thousands of paths - keep them cheap: one
> `<line>` each, no per-frame work, paths faint until their marker is active.)
>
> ### Marker visualisation - colour by team, shape by outcome
> - Each shot is an SVG `<circle>` at its origin, radius by xG:
>   `r = clamp(3.5 + xg*12, 3, 14)`. Bigger dot = higher chance.
> - **Colour encodes the team** (`LEAGUE.teams[t].color`), so a filtered team's
>   shots read as one colour block. **Outcome is encoded by treatment**, layered
>   on the team colour so both are legible at once:
>   - **Goal** - solid team colour, bold white ring.
>   - **On target (saved)** - solid team colour, thin ring.
>   - **Off target** - hollow (team-colour ring, near-transparent fill).
>   - **Blocked** - near-black fill, team-colour ring.
> - Because the pitch is dark navy, **brighten/tint each team colour for
>   contrast** (as the site's match-centre already does) - dark navies and
>   blacks (e.g. Chelsea, Tottenham, Newcastle, Everton) must be lifted or they
>   vanish. Provide a "colour by outcome" toggle (the single-player scheme -
>   gradient goal / pale on-target / hollow off / dark blocked) for when a
>   single team or player is selected.
> - Path colour follows its marker's team colour; goals' paths are boldest, the
>   rest faint until the marker is hovered/focused, then that path lights up.
>
> ### Filters & aggregates
> - Filter bar over the shot map: **Team**, **Player** (populated from the
>   selected team), **Matchday** range, **Situation**, **Body part**,
>   **Outcome**. Filters compose; the map, the stat strip and (for team) the
>   table highlight stay in sync. All filtering is client-side over the loaded
>   arrays.
> - Stat strip recomputed from the current filter: **Shots**, **Goals**,
>   **Total xG** (1 dp), **xG/shot** (2 dp), and **G - xG** (finishing
>   over/under-performance). With a single player selected it mirrors the
>   Yamal map's Shots / Goals / Total xG.
>
> ### Interaction & accessibility
> - Hover / focus / tap a shot -> highlight the dot, light its path, show a
>   tooltip (`player` (`team`) vs `opp`, `min`' - `body` - `situ`, xG `x.xx`,
>   outcome) and mirror it into a caption under the map.
> - Every marker keyboard-focusable (`tabindex="0"`, `role="img"`) with an
>   `aria-label` summarising player, team, minute, outcome and xG. Table is a
>   real `<table>` with sortable `<th aria-sort>`. Tooltip follows the pointer;
>   a click outside any shot dismisses it.
>
> ### Non-negotiables
> - Vanilla JS + SVG only; graceful fallback data; works with JS off.
> - Deterministic direction fan (no `Math.random()` in path endpoints).
> - Real `gy` always overrides the fallback endpoint.
> - Goals drawn last (markers and paths). Team colours brightened for the dark
>   pitch. One `LEAGUE` config switches between xLaLiga and xEPL.

---

## League configs

Illustrative primaries - tune each for contrast on the dark navy pitch (lift
navies/blacks; disambiguate the many reds with secondary rings or labels).

### xLaLiga (2025/26) - `slug: "laliga"`

| Team              | Colour   | Team              | Colour   |
| ----------------- | -------- | ----------------- | -------- |
| Barcelona         | #A50044  | Real Madrid       | #FEBE10  |
| Atletico Madrid   | #CB3524  | Athletic Club     | #EE2523  |
| Villarreal        | #FFD000  | Real Betis        | #00954C  |
| Celta Vigo        | #6FB4E8  | Rayo Vallecano    | #E53027  |
| Osasuna           | #C4122E  | Mallorca          | #E20613  |
| Real Sociedad     | #3B6AB4  | Valencia          | #F18E00  |
| Getafe            | #1B69B4  | Espanyol          | #12A0DE  |
| Sevilla           | #F43333  | Girona            | #D81E05  |
| Deportivo Alaves  | #2E7BD6  | Levante           | #B4053F  |
| Elche             | #22A65A  | Real Oviedo       | #2E6FC0  |

### xEPL (2025/26) - `slug: "epl"`

| Team              | Colour   | Team              | Colour   |
| ----------------- | -------- | ----------------- | -------- |
| Liverpool         | #C8102E  | Arsenal           | #EF0107  |
| Manchester City   | #6CABDD  | Chelsea           | #2A6EDB  |
| Newcastle         | #B9C0C7  | Aston Villa       | #95214B  |
| Nottingham Forest | #DD0000  | Brighton          | #0057B8  |
| Bournemouth       | #DA291C  | Crystal Palace    | #2A5FC0  |
| Brentford         | #E30613  | Fulham            | #D0D0D0  |
| Manchester United | #DA291C  | Tottenham         | #5C74C0  |
| West Ham          | #A23751  | Everton           | #2C5AD8  |
| Wolverhampton     | #FDB913  | Leeds United      | #3A6BD6  |
| Burnley           | #8A2A57  | Sunderland        | #EB172B  |

Config shape:

```js
const LEAGUE = {
  name: "xLaLiga", slug: "laliga",
  shots: "assets/data/laliga/shots.json",
  results: "assets/data/laliga/results.json",
  teams: { "Barcelona": { color: "#A50044" }, /* ...20 teams... */ },
};
// swap name/slug/teams for xEPL - all rendering code is unchanged.
```

---

## Relationship to the single-player map & anchors

Same engine, wider lens: the pitch geometry, the `goalEndX` direction fan and
the xG-radius markers are identical to `docs/lamine-yamal-xg-map.prompt.md`; the
league version adds `team`/`opp`/`player` to each shot, colour-by-team, filters,
and the xG table. Anchor points to reuse:

| Concern              | Where                                                 |
| -------------------- | ----------------------------------------------------- |
| Path endpoint / fan  | `main.js` - `goalEndX(s)`, `hash01(s)`                |
| Path + block-shorten | `main.js` - `makePath(s)`                             |
| Marker + xG radius   | `main.js` - `makeDot(s)`, `radius(xg)`                |
| Team-coloured shots  | `styles.css` - `.mc-shot.home/.away` (brighten pattern) |
| Pitch / goal SVG     | `index.html` - `#shotmap` (`GOAL_X/Y`, `GOAL_SCALE`)  |
| xG aggregation/table | new - fold `shots.json` + `results.json` per team     |
