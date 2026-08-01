"""Position-battle race — a line of cars that swap order as the race unfolds.

Consumes the tidy lap log from ``scraper.py`` (``data/race_data.csv``) and
animates every driver as a little car. All cars sit on the **same vertical line**
(the current lap) and slide up and down between position lanes as the running
order changes lap-by-lap — you literally watch them overtake each other. The
field sweeps left→right toward the finish line as the laps tick by.

Because it is driven purely by the position log, it needs no telemetry.

Saved as ``latest_race_replay.mp4``.

Run standalone::

    python race_animator.py
    python race_animator.py --fps 24 --frames-per-lap 6
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
from matplotlib import patheffects
from matplotlib import pyplot as plt
from matplotlib.animation import FFMpegWriter, FuncAnimation

import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s"
)
log = logging.getLogger("race_animator")


def load_data(laps_csv: Path = config.LAPS_CSV, meta_json: Path = config.META_JSON):
    if not laps_csv.exists() or not meta_json.exists():
        raise FileNotFoundError(
            f"Missing scraped data ({laps_csv} / {meta_json}). Run scraper.py first."
        )
    df = pd.read_csv(laps_csv)
    with meta_json.open(encoding="utf-8") as fh:
        meta = json.load(fh)
    return df, meta


def _configure_ffmpeg() -> None:
    if shutil.which("ffmpeg"):
        return
    try:
        import imageio_ffmpeg

        matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
        log.info("Using bundled ffmpeg from imageio-ffmpeg.")
    except Exception:  # pragma: no cover
        log.warning("No ffmpeg found; MP4 export may fail.")


class PositionRace:
    """Animate the field as cars that swap position lanes over the race."""

    def __init__(self, df, meta, fps=24, frames_per_lap=6, width=1280, height=720,
                 dpi=100, hold_end_seconds=2.5):
        self.df = df.copy()
        self.meta = meta
        self.fps = fps
        self.frames_per_lap = max(1, frames_per_lap)
        self.dpi, self.width, self.height = dpi, width, height
        self.hold_end_frames = int(hold_end_seconds * fps)

        self.total_laps = int(meta.get("total_laps") or df["LapNumber"].max())
        self.vsc_laps = set(meta.get("vsc_laps", []))
        self.driver_meta = meta.get("drivers", {})

        self._prepare()
        self._setup_figure()
        self._create_artists()

    # -- data ---------------------------------------------------------------- #
    def _prepare(self):
        self.drivers, self.series = [], {}
        for abbr in self.df["Driver"].dropna().unique():
            d = (self.df[self.df["Driver"] == abbr]
                 .sort_values("LapNumber").drop_duplicates("LapNumber"))
            laps = d["LapNumber"].to_numpy(dtype=float)
            pos = pd.to_numeric(d["Position"], errors="coerce").to_numpy(dtype=float)
            valid = ~np.isnan(pos)
            if valid.sum() == 0:
                continue
            info = self.driver_meta.get(abbr, {})
            last_pos = float(pos[valid][-1])
            classified = info.get("classified")
            # Retired drivers get parked at their official classification (which
            # already ranks DNFs at the bottom); finishers settle where they end.
            settle_pos = float(classified) if classified is not None else last_pos
            self.drivers.append(abbr)
            self.series[abbr] = {
                "laps": laps[valid], "pos": pos[valid],
                "first_lap": float(laps[valid][0]), "last_lap": float(laps[valid][-1]),
                "compound": dict(zip(d["LapNumber"].astype(int), d["Compound"])),
                "pits": set(int(x) for x in d.loc[d.get("is_pit_stop", False) == True, "LapNumber"]),
                "color": info.get("color") or "#CCCCCC",
                "is_retired": not info.get("finished", True),
                "settle_pos": settle_pos,
            }
        positions = pd.to_numeric(self.df["Position"], errors="coerce")
        classified_positions = [
            s["settle_pos"] for s in self.series.values()
        ] + ([np.nanmax(positions)] if positions.notna().any() else [20])
        self.num_positions = int(max(classified_positions))

    def _compound_at(self, abbr, lap):
        comp = self.series[abbr]["compound"]
        if lap in comp:
            return comp[lap]
        earlier = [l for l in comp if l <= lap]
        return comp[max(earlier)] if earlier else "UNKNOWN"

    # -- figure -------------------------------------------------------------- #
    def _setup_figure(self):
        self.fig = plt.figure(figsize=(self.width / self.dpi, self.height / self.dpi),
                              dpi=self.dpi)
        self.fig.patch.set_facecolor(config.THEME["figure_bg"])
        self.ax = self.fig.add_axes([0.05, 0.09, 0.90, 0.78])
        ax = self.ax
        ax.set_facecolor(config.THEME["axes_bg"])
        ax.set_xlim(0.3, self.total_laps + 0.7)
        ax.set_ylim(self.num_positions + 0.6, 0.4)      # inverted: P1 on top

        # Alternating lane bands so each position row is easy to track.
        for p in range(1, self.num_positions + 1):
            ax.axhspan(p - 0.5, p + 0.5, zorder=0,
                       color=config.RACE["lane_alt"] if p % 2 else config.RACE["lane"])

        step = 5 if self.total_laps <= 60 else 10
        xticks = [1] + list(range(step, self.total_laps + 1, step))
        ax.set_xticks(sorted(set(xticks)))
        ax.set_yticks(range(1, self.num_positions + 1))
        ax.set_yticklabels([f"P{i}" for i in range(1, self.num_positions + 1)])
        ax.tick_params(colors=config.THEME["text_secondary"], labelsize=9, length=0)
        ax.set_xlabel("Lap", color=config.THEME["text_secondary"], fontsize=11)
        for s in ax.spines.values():
            s.set_color(config.THEME["spine"])
            s.set_linewidth(0.8)

        # Finish line at the last lap.
        ax.axvline(self.total_laps, color=config.RACE["finish"], lw=1.6, alpha=0.55,
                   zorder=1)
        ax.text(self.total_laps, 0.28, "FINISH", color=config.RACE["finish"],
                fontsize=8, fontweight="bold", ha="center", va="bottom", alpha=0.8)

        # Header
        title = f"{self.meta.get('year','')} {self.meta.get('event_name','Grand Prix')}".strip()
        self.fig.text(0.05, 0.955, title, color=config.THEME["text_primary"],
                      fontsize=18, fontweight="bold", va="center")
        self.fig.text(0.05, 0.918, "Battle for Position", color=config.THEME["text_secondary"],
                      fontsize=11, va="center")
        self.fig.text(0.985, 0.02, "F1Visualized", color=config.THEME["text_secondary"],
                      fontsize=9, ha="right", va="center", alpha=0.7)
        self.lap_counter = self.fig.text(0.95, 0.94, "", color=config.THEME["text_primary"],
                                         fontsize=20, fontweight="bold", ha="right", va="center")
        self.vsc_banner = self.fig.text(
            0.5, 0.905, "  VIRTUAL SAFETY CAR  ", ha="center", va="center",
            fontsize=13, fontweight="bold", color="#15151C", zorder=30, visible=False,
            bbox=dict(boxstyle="round,pad=0.4", fc=config.THEME["vsc"], ec="none"))

    def _create_artists(self):
        stroke = [patheffects.withStroke(linewidth=2.2, foreground="#101015")]
        car = config.car_marker()
        self.cars, self.names, self.badges = {}, {}, {}
        for abbr in self.drivers:
            c = self.series[abbr]["color"]
            (self.cars[abbr],) = self.ax.plot(
                [], [], marker=car, markersize=config.CAR_MARKER_SIZE, mfc=c,
                mec="white", mew=0.6, linestyle="None", zorder=5)
            self.names[abbr] = self.ax.annotate(
                abbr, xy=(0, 0), xytext=(6, 13), textcoords="offset points",
                ha="left", va="center", color="white", fontsize=8, fontweight="bold",
                zorder=7, path_effects=stroke, annotation_clip=False)
            self.badges[abbr] = self.ax.annotate(
                "", xy=(0, 0), xytext=(-9, 13), textcoords="offset points",
                ha="center", va="center", fontsize=7.5, fontweight="bold",
                zorder=7, annotation_clip=False)

    # -- update -------------------------------------------------------------- #
    @property
    def n_frames(self):
        return (self.total_laps - 1) * self.frames_per_lap + 1 + self.hold_end_frames

    def _frame_to_lap(self, frame):
        main = (self.total_laps - 1) * self.frames_per_lap
        return 1.0 + min(frame, main) / self.frames_per_lap

    def update(self, frame):
        cl = self._frame_to_lap(frame)
        current_lap = int(np.clip(np.floor(cl), 1, self.total_laps))
        self.lap_counter.set_text(f"LAP {current_lap} / {self.total_laps}")

        for abbr in self.drivers:
            s = self.series[abbr]
            car, name, badge = self.cars[abbr], self.names[abbr], self.badges[abbr]

            if cl < s["first_lap"]:
                for art in (car, name, badge):
                    art.set_visible(False)
                continue

            if cl >= s["last_lap"]:                       # settled (finished/retired)
                prog = min(1.0, cl - s["last_lap"])       # slide to final slot over ~1 lap
                ease = prog * prog * (3 - 2 * prog)
                x = cl                                    # stays on the current-lap line
                y = s["pos"][-1] + (s["settle_pos"] - s["pos"][-1]) * ease
                car.set_visible(True); car.set_data([x], [y])
                car.set_markeredgecolor("white")
                name.set_visible(True); name.xy = (x, y)
                if s["is_retired"]:                       # drop to last, dim, behind field
                    alpha = 1.0 - 0.55 * ease
                    car.set_alpha(alpha); car.set_zorder(3)
                    name.set_alpha(alpha); name.set_zorder(4)
                    badge.set_visible(False)
                else:
                    car.set_alpha(1.0); car.set_zorder(5)
                    name.set_alpha(1.0)
                    self._set_badge(badge, x, y, self._compound_at(abbr, current_lap), False)
                continue

            # Active: all cars share x = current lap; y slides between positions.
            y = float(np.interp(cl, s["laps"], s["pos"]))
            in_pit = current_lap in s["pits"]
            car.set_visible(True); car.set_data([cl], [y]); car.set_alpha(1.0)
            car.set_markeredgecolor(config.THEME["pit"] if in_pit else "white")
            name.set_visible(True); name.xy = (cl, y); name.set_alpha(1.0)
            self._set_badge(badge, cl, y, self._compound_at(abbr, current_lap), in_pit)

        on_vsc = current_lap in self.vsc_laps
        self.vsc_banner.set_visible(on_vsc and (frame // max(1, self.fps // 6)) % 2 == 0)
        return []

    def _set_badge(self, badge, x, y, compound, in_pit):
        badge.set_visible(True)
        badge.xy = (x, y)
        if in_pit:
            badge.set_text("P")
            badge.set_color("white")
            badge.set_bbox(dict(boxstyle="circle,pad=0.22", fc=config.THEME["pit"], ec="none"))
        else:
            st = config.compound_style(compound)
            badge.set_text(st["letter"])
            badge.set_color(st["text"])
            badge.set_bbox(dict(boxstyle="circle,pad=0.22", fc=st["color"], ec="none"))

    def render(self, output_path: Path = config.OUTPUT_REPLAY, bitrate=4600):
        _configure_ffmpeg()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        anim = FuncAnimation(self.fig, self.update, frames=self.n_frames,
                             interval=1000 / self.fps, blit=False)
        writer = FFMpegWriter(fps=self.fps, codec="libx264", bitrate=bitrate,
                              extra_args=["-pix_fmt", "yuv420p"])
        log.info("Rendering %d frames (%d cars, %d laps) -> %s",
                 self.n_frames, len(self.drivers), self.total_laps, output_path)
        anim.save(str(output_path), writer=writer, dpi=self.dpi)
        plt.close(self.fig)
        log.info("Saved %s", output_path)
        return output_path


def animate(output_path: Path = config.OUTPUT_REPLAY, fps=24, frames_per_lap=6,
            width=1280, height=720) -> Path:
    df, meta = load_data()
    return PositionRace(df, meta, fps=fps, frames_per_lap=frames_per_lap,
                        width=width, height=height).render(output_path)


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="Render the F1 position-battle race MP4.")
    p.add_argument("--output", type=Path, default=config.OUTPUT_REPLAY)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--frames-per-lap", type=int, default=6, dest="frames_per_lap")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    animate(output_path=args.output, fps=args.fps, frames_per_lap=args.frames_per_lap,
            width=args.width, height=args.height)


if __name__ == "__main__":
    main()
