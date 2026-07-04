# Prompt - Lamine Yamal xG shot map

A self-contained brief for (re)building the interactive **Lamine Yamal xG shot
map** on this site. It is written so an LLM or a developer can reproduce the
component exactly, with special emphasis on the two things that make or break
it: the **kicked-ball direction** (where each shot's path ends on the goal) and
the **visualisation** (how markers and paths are drawn, sized and styled).

The live implementation lives in `main.js` (the block under
"Lamine Yamal - xG shot map"), `index.html` (the `#shotmap` SVG) and
`styles.css` (`.shot`, `.shot-path`). Data is `assets/data/yamal_shots.json`.

---

## The prompt

> Build a dependency-free, interactive **expected-goals (xG) shot map** for
> Lamine Yamal's 2025/26 season (all competitions), rendered as inline SVG and
> driven by real event data. No chart library, no framework - plain SVG built
> with the DOM API. The page must be fully readable without JS; the map is a
> progressive enhancement layered on top.
>
> ### Data
> Load `assets/data/yamal_shots.json`: an array of shot objects. Fall back to a
> small hard-coded array if the fetch fails. Each shot:
>
> ```json
> { "x": 383.5, "y": 154.9, "xg": 0.095, "min": 72,
>   "out": "goal", "body": "Left foot", "note": "Real Oviedo",
>   "situ": "Open play", "gy": 53 }
> ```
>
> - `x`, `y` - shot **origin** on the pitch, in the SVG's coordinate space
>   (the goal is at the **top**; larger `y` = further from goal).
> - `xg` - expected-goals value in `[0,1]` (a geometry-based model estimate).
> - `min` - match minute. `out` - outcome, one of
>   `goal | saved (on target) | off (off target) | blocked`.
> - `body` - `Left foot | Right foot | Header`. `situ` - situation
>   (`Open play`, `Penalty`, `Fast break`, `Corner`, `Free kick`, ...).
> - `note` - opponent (shown as "vs ..."). `gy` - **optional** WhoScored
>   `goalMouthY` (0-100): where the ball actually crossed the goal line.
>   `50` = dead centre, `~45 / ~55` = the posts. When present it is the ground
>   truth for the shot's direction; when absent, derive a plausible endpoint
>   (see **Kicked-ball direction** below).
>
> ### Pitch geometry (attacking half, goal on top)
> - SVG `viewBox="0 0 680 520"`; draw the attacking half of a pitch with the
>   goal line across the **top**.
> - Constants: `GOAL_X = 340` (goal-mouth centre = horizontal centre),
>   `GOAL_Y = 30` (the goal line), goalposts at `x = 308` and `x = 372`
>   (a 64px goal). `GOAL_SCALE = 6.4` px per `goalMouthY` unit, so
>   `x = GOAL_X + (gy - 50) * GOAL_SCALE` maps `gy 45/55` onto the posts.
> - Render the box, six-yard box, penalty arc and centre circle arc as faint
>   white strokes on a dark navy pitch; draw the goal as a short bar on the
>   goal line and the penalty spot as a small dot.
> - Two ordered SVG groups: `#pathLayer` (shot paths, drawn first / underneath)
>   then `#shotLayer` (markers, on top). Within each, draw non-goals first and
>   **goals last** so goals sit on top.
>
> ### Kicked-ball direction (the shot path) - the important part
> Every shot draws a straight path from its origin `(x, y)` to a point on the
> goal line. **Do not send every path to the goal centre** - if you do, all
> shots collapse onto one pixel and the map turns into a meaningless starburst
> where even misses appear aimed dead centre. Instead compute a distinct
> endpoint per shot with this precedence:
>
> 1. **Measured data wins.** If the shot has a numeric `gy`, end the path at
>    the real crossing point: `endX = GOAL_X + (gy - 50) * GOAL_SCALE`,
>    `endY = GOAL_Y`. This is the true kicked-ball direction and always
>    overrides the fallback.
>
> 2. **No `gy` -> a stable, outcome-aware fan across the goal mouth.** Give each
>    shot a **deterministic** jitter (a hash of `x`, `y`, `min` -> `[0,1)`, e.g.
>    `sin(x*12.9898 + y*78.233 + min*37.719) * 43758.5453`, take the fractional
>    part). Deterministic matters: the fan must be stable across re-renders, not
>    random flicker. Then, using `jit = hash - 0.5`:
>    - **Off target (`off`):** end **wide of a post**, on the side the shot came
>      from. `side = x >= GOAL_X ? +1 : -1;
>      endX = GOAL_X + side * (42 + |jit| * 26)`. A miss must visibly miss.
>    - **On target / blocked:** lean gently toward the shooter's side and spread
>      to fill the mouth: `lean = (x - GOAL_X) / 40;
>      endX = clamp(GOAL_X + lean + jit * 50, 311, 369)` (just inside the posts).
>    - **Blocked (`blocked`):** the ball never reaches the line - after choosing
>      `endX`, shorten the whole path to **60%** of its length
>      (`ex = x + (ex - x) * 0.6`, `ey = y + (ey - y) * 0.6`) so it stops en
>      route, where a defender got in the way.
>
> The result: paths radiate naturally across the entire goal mouth, misses
> splay outside the posts, blocks die partway, and any shot with a real `gy`
> snaps to exactly where the ball went. Add a real `gy` later and that shot
> corrects itself with no other change.
>
> ### Marker visualisation
> - Each shot is an SVG `<circle>` at its origin `(x, y)`, radius scaled by xG:
>   `r = clamp(3.5 + xg * 12, 3, 14)`. Bigger dot = higher chance.
> - Style by outcome (this is the visual legend):
>   - **Goal** - filled with a blue->crimson (Blaugrana) gradient, thin white ring.
>   - **On target (saved)** - solid pale fill, faint dark ring.
>   - **Off target** - hollow (near-transparent fill), visible white ring.
>   - **Blocked** - near-black fill, faint white ring.
> - Path styling: goals' paths are the boldest/most opaque; on-target, off and
>   blocked paths are faint until their marker is hovered/focused, at which
>   point the matching path lights up (`.lit`: bright white, full opacity).
>
> ### Interaction & accessibility
> - Hover, focus or tap a shot -> highlight the dot, light its path, and show a
>   tooltip: "vs {opponent}", "{min}' - {body} - {situ}", "xG {x.xx}" and the
>   outcome label. Mirror the same line into a persistent caption under the map.
> - Every marker is keyboard-focusable (`tabindex="0"`, `role="img"`) with an
>   `aria-label` summarising opponent, minute, outcome and xG. Tooltip follows
>   the pointer on `mousemove`; a document click outside any shot dismisses it.
> - Below the map show a stat strip computed from the data: **Shots** (count),
>   **Goals** (count of `out === "goal"`) and **Total xG** (sum of `xg`,
>   1 decimal), plus a legend for the four outcome styles, "size = xG" and
>   "shot path -> goal".
>
> ### Non-negotiables
> - Vanilla JS + SVG only; graceful fallback data; content works with JS off.
> - Deterministic fan (no `Math.random()` in the path endpoints).
> - Real `gy` always overrides the fallback endpoint.
> - Goals drawn last (markers and paths) so they read on top.

---

## Why the direction logic exists (context)

An earlier version drew every shot's path to the goal-mouth **centre**
(`GOAL_X, GOAL_Y`). Because that endpoint was a constant, all ~150 paths
converged on a single point: the map looked like every shot was aimed straight
down the middle, and misses "hit" the centre too. The `goalEndX()` fan above
replaced that constant with a per-shot endpoint - measured `gy` when we have
it, otherwise a stable outcome-aware spread - so the paths finally show
direction instead of stacking. See `main.js` -> `goalEndX` / `makePath`.

## Quick reference (implementation anchors)

| Concern              | Where                                             |
| -------------------- | ------------------------------------------------- |
| Path endpoint / fan  | `main.js` - `goalEndX(s)`, `hash01(s)`            |
| Path + block-shorten | `main.js` - `makePath(s)`                         |
| Marker + xG radius   | `main.js` - `makeDot(s)`, `radius(xg)`            |
| Pitch / goal SVG     | `index.html` - `#shotmap` (`GOAL_X/Y`, `GOAL_SCALE`) |
| Outcome styles       | `styles.css` - `.shot.*`, `.shot-path.*`, `.lit`  |
| Data                 | `assets/data/yamal_shots.json`                    |
