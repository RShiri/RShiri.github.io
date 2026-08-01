"""Stage 2 — Video visualisation engine.

Consumes the tidy table written by ``scraper.py`` and renders an MP4 that
mirrors the *F1Visualized* race-timelapse style:

* dark-grey canvas, x-axis = lap number, y-axis = grid position **inverted**
  (P1 at the top, P20 at the bottom);
* one moving, team-coloured trace per driver with the 3-letter abbreviation
  riding at the head of the line;
* a colour-coded tyre badge (Red ``[S]`` / Yellow ``[M]`` / White ``[H]`` / ...)
  beside each name;
* a green ``[IN PIT]`` tag on the lap a driver pits;
* a flashing yellow **VIRTUAL SAFETY CAR** banner while a VSC is deployed.

The timeline is animated lap-by-lap with :class:`matplotlib.animation.FuncAnimation`
(with sub-lap interpolation for smooth motion) and saved as
``latest_race_timelapse.mp4``.

Run standalone::

    python animator.py                       # uses data/ + default output
    python animator.py --fps 24 --frames-per-lap 5
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # headless / CI-safe backend

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.animation import FFMpegWriter, FuncAnimation

import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s"
)
log = logging.getLogger("animator")


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_data(
    laps_csv: Path = config.LAPS_CSV, meta_json: Path = config.META_JSON
) -> tuple[pd.DataFrame, dict]:
    if not laps_csv.exists() or not meta_json.exists():
        raise FileNotFoundError(
            f"Missing scraped data ({laps_csv} / {meta_json}). Run scraper.py first."
        )
    df = pd.read_csv(laps_csv)
    with meta_json.open(encoding="utf-8") as fh:
        meta = json.load(fh)
    return df, meta


def _configure_ffmpeg() -> None:
    """Make sure matplotlib can find an ffmpeg binary.

    Prefers a system ffmpeg (installed by the CI workflow); otherwise falls
    back to the one bundled with ``imageio-ffmpeg`` so local runs work too.
    """
    if shutil.which("ffmpeg"):
        return
    try:
        import imageio_ffmpeg

        matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
        log.info("Using bundled ffmpeg from imageio-ffmpeg.")
    except Exception:  # pragma: no cover
        log.warning(
            "No system ffmpeg and imageio-ffmpeg unavailable; MP4 export may fail."
        )


# --------------------------------------------------------------------------- #
# The timelapse
# --------------------------------------------------------------------------- #
class RaceTimelapse:
    """Builds and renders the lap-by-lap position animation."""

    def __init__(
        self,
        df: pd.DataFrame,
        meta: dict,
        fps: int = 24,
        frames_per_lap: int = 5,
        width: int = 1280,
        height: int = 720,
        dpi: int = 100,
        hold_end_seconds: float = 2.5,
    ) -> None:
        self.df = df.copy()
        self.meta = meta
        self.fps = fps
        self.frames_per_lap = max(1, frames_per_lap)
        self.dpi = dpi
        self.width, self.height = width, height
        self.hold_end_frames = int(hold_end_seconds * fps)

        self.total_laps = int(meta.get("total_laps") or df["LapNumber"].max())
        self.vsc_laps = set(meta.get("vsc_laps", []))
        self.driver_meta = meta.get("drivers", {})

        self._prepare_driver_series()
        self._setup_figure()
        self._create_artists()

    # -- data preparation --------------------------------------------------- #
    def _prepare_driver_series(self) -> None:
        """Pre-compute per-driver arrays used every frame (fast + clean)."""
        self.drivers: list[str] = []
        self.series: dict[str, dict] = {}

        # Draw order: final classification if known, else by finishing position.
        present = [d for d in self.df["Driver"].dropna().unique()]
        for abbr in present:
            d = (
                self.df[self.df["Driver"] == abbr]
                .sort_values("LapNumber")
                .drop_duplicates("LapNumber")
            )
            laps = d["LapNumber"].to_numpy(dtype=float)
            pos = pd.to_numeric(d["Position"], errors="coerce").to_numpy(dtype=float)
            valid = ~np.isnan(pos)
            if valid.sum() == 0:
                continue
            self.drivers.append(abbr)
            self.series[abbr] = {
                "laps": laps[valid],
                "pos": pos[valid],
                "first_lap": float(laps[valid][0]),
                "last_lap": float(laps[valid][-1]),
                "compound": dict(zip(d["LapNumber"].astype(int), d["Compound"])),
                "pits": set(
                    int(x) for x in d.loc[d.get("is_pit_stop", False) == True, "LapNumber"]
                ),
                "color": self._driver_color(abbr),
            }

        positions = pd.to_numeric(self.df["Position"], errors="coerce")
        self.num_positions = int(np.nanmax(positions)) if positions.notna().any() else 20

    def _driver_color(self, abbr: str) -> str:
        info = self.driver_meta.get(abbr, {})
        return info.get("color") or "#CCCCCC"

    def _compound_at(self, abbr: str, lap: int) -> str:
        comp = self.series[abbr]["compound"]
        if lap in comp:
            return comp[lap]
        earlier = [l for l in comp if l <= lap]
        return comp[max(earlier)] if earlier else "UNKNOWN"

    # -- figure / axes ------------------------------------------------------ #
    def _setup_figure(self) -> None:
        self.fig = plt.figure(
            figsize=(self.width / self.dpi, self.height / self.dpi), dpi=self.dpi
        )
        self.fig.patch.set_facecolor(config.THEME["figure_bg"])
        # Left margin for P-labels, generous right margin for the head labels,
        # and a header band above the plot for the title + VSC banner.
        self.ax = self.fig.add_axes([0.055, 0.085, 0.80, 0.78])
        ax = self.ax
        ax.set_facecolor(config.THEME["axes_bg"])

        ax.set_xlim(0.4, self.total_laps + 0.6)
        ax.set_ylim(self.num_positions + 0.6, 0.4)  # inverted: P1 on top

        # Ticks
        step = 5 if self.total_laps <= 60 else 10
        xticks = list(range(step, self.total_laps + 1, step))
        if 1 not in xticks:
            xticks = [1] + xticks
        ax.set_xticks(xticks)
        ax.set_yticks(range(1, self.num_positions + 1))
        ax.set_yticklabels([f"P{i}" for i in range(1, self.num_positions + 1)])
        ax.tick_params(colors=config.THEME["text_secondary"], labelsize=9, length=0)

        ax.set_xlabel("Lap", color=config.THEME["text_secondary"], fontsize=11)

        # Recessive grid + spines
        ax.grid(axis="x", color=config.THEME["grid"], linewidth=0.6, alpha=0.5)
        ax.grid(axis="y", color=config.THEME["grid"], linewidth=0.4, alpha=0.3)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color(config.THEME["spine"])
            spine.set_linewidth(0.8)

        # Header
        title = f"{self.meta.get('year','')} {self.meta.get('event_name','Grand Prix')}"
        self.fig.text(
            0.055, 0.958, title.strip(), color=config.THEME["text_primary"],
            fontsize=18, fontweight="bold", ha="left", va="center",
        )
        self.fig.text(
            0.055, 0.921, "Race • Position by Lap", color=config.THEME["text_secondary"],
            fontsize=11, ha="left", va="center",
        )
        self.fig.text(
            0.985, 0.02, "F1Visualized", color=config.THEME["text_secondary"],
            fontsize=9, ha="right", va="center", alpha=0.7,
        )
        # Live lap counter (updated per frame)
        self.lap_counter = self.fig.text(
            0.855, 0.945, "", color=config.THEME["text_primary"],
            fontsize=20, fontweight="bold", ha="right", va="center",
        )

    def _create_artists(self) -> None:
        theme = config.THEME
        self.lines: dict[str, plt.Line2D] = {}
        self.names: dict[str, matplotlib.text.Annotation] = {}
        self.badges: dict[str, matplotlib.text.Annotation] = {}
        self.pits: dict[str, matplotlib.text.Annotation] = {}

        for abbr in self.drivers:
            color = self.series[abbr]["color"]
            (line,) = self.ax.plot(
                [], [], color=color, linewidth=2.0, solid_capstyle="round",
                alpha=0.9, zorder=4,
            )
            self.lines[abbr] = line

            self.names[abbr] = self.ax.annotate(
                abbr, xy=(0, 0), xytext=(9, 0), textcoords="offset points",
                ha="left", va="center", color=color, fontsize=11,
                fontweight="bold", zorder=6, clip_on=False, annotation_clip=False,
            )
            self.badges[abbr] = self.ax.annotate(
                "", xy=(0, 0), xytext=(45, 0), textcoords="offset points",
                ha="center", va="center", fontsize=9.5, fontweight="bold",
                zorder=6, clip_on=False, annotation_clip=False,
            )
            self.pits[abbr] = self.ax.annotate(
                "[IN PIT]", xy=(0, 0), xytext=(61, 0), textcoords="offset points",
                ha="left", va="center", color=theme["pit"], fontsize=8.5,
                fontweight="bold", zorder=6, clip_on=False, annotation_clip=False,
                visible=False,
            )

        # Flashing VSC banner — pinned in the header band so it never covers a
        # driver's head label. Centred over the plot; toggled per frame.
        self.vsc_banner = self.fig.text(
            0.455, 0.905, "  VIRTUAL SAFETY CAR  ",
            ha="center", va="center", fontsize=14, fontweight="bold",
            color="#15151C", zorder=30, visible=False,
            bbox=dict(boxstyle="round,pad=0.4", fc=theme["vsc"], ec="none"),
        )

    # -- per-frame update --------------------------------------------------- #
    @property
    def n_frames(self) -> int:
        return (self.total_laps - 1) * self.frames_per_lap + 1 + self.hold_end_frames

    def _frame_to_lap(self, frame: int) -> float:
        main = (self.total_laps - 1) * self.frames_per_lap
        j = min(frame, main)
        return 1.0 + j / self.frames_per_lap

    def update(self, frame: int):
        cl = self._frame_to_lap(frame)           # continuous lap position
        current_lap = int(np.clip(np.floor(cl), 1, self.total_laps))
        self.lap_counter.set_text(f"LAP {current_lap} / {self.total_laps}")

        for abbr in self.drivers:
            s = self.series[abbr]
            line, name = self.lines[abbr], self.names[abbr]
            badge, pit = self.badges[abbr], self.pits[abbr]

            if cl < s["first_lap"]:  # driver hasn't taken a recorded lap yet
                line.set_data([], [])
                for art in (name, badge, pit):
                    art.set_visible(False)
                continue

            if cl >= s["last_lap"]:  # settled at last recorded point
                head_x, head_y = s["last_lap"], s["pos"][-1]
                line.set_data(s["laps"], s["pos"])
                finished = s["last_lap"] >= self.total_laps
                name.set_visible(True)
                name.set_alpha(1.0 if finished else 0.35)  # dim genuine DNFs
                name.xy = (head_x, head_y)
                pit.set_visible(False)
                if finished:  # keep the final tyre badge on classified finishers
                    style = config.compound_style(
                        self._compound_at(abbr, int(s["last_lap"]))
                    )
                    badge.set_visible(True)
                    badge.xy = (head_x, head_y)
                    badge.set_text(style["letter"])
                    badge.set_color(style["text"])
                    badge.set_bbox(
                        dict(boxstyle="round,pad=0.28", fc=style["color"], ec="none")
                    )
                else:
                    badge.set_visible(False)
                continue

            # Active: interpolate the head for smooth vertical motion
            head_y = float(np.interp(cl, s["laps"], s["pos"]))
            mask = s["laps"] <= cl
            xs = np.append(s["laps"][mask], cl)
            ys = np.append(s["pos"][mask], head_y)
            line.set_data(xs, ys)

            name.set_visible(True)
            name.set_alpha(1.0)
            name.xy = (cl, head_y)

            style = config.compound_style(self._compound_at(abbr, current_lap))
            badge.set_visible(True)
            badge.xy = (cl, head_y)
            badge.set_text(style["letter"])
            badge.set_color(style["text"])
            badge.set_bbox(
                dict(boxstyle="round,pad=0.28", fc=style["color"], ec="none")
            )

            in_pit = current_lap in s["pits"]
            pit.set_visible(in_pit)
            if in_pit:
                pit.xy = (cl, head_y)

        # VSC banner: visible on VSC laps, flashing at ~3 Hz
        on_vsc = current_lap in self.vsc_laps
        flash_period = max(1, self.fps // 6)
        show = on_vsc and (frame // flash_period) % 2 == 0
        self.vsc_banner.set_visible(show)
        return []

    # -- render ------------------------------------------------------------- #
    def render(self, output_path: Path = config.OUTPUT_VIDEO, bitrate: int = 4200) -> Path:
        _configure_ffmpeg()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        anim = FuncAnimation(
            self.fig, self.update, frames=self.n_frames,
            interval=1000 / self.fps, blit=False,
        )
        writer = FFMpegWriter(
            fps=self.fps, codec="libx264", bitrate=bitrate,
            extra_args=["-pix_fmt", "yuv420p"],
        )
        log.info(
            "Rendering %d frames (%d drivers, %d laps) -> %s",
            self.n_frames, len(self.drivers), self.total_laps, output_path,
        )
        anim.save(str(output_path), writer=writer, dpi=self.dpi)
        plt.close(self.fig)
        log.info("Saved %s", output_path)
        return output_path


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def animate(
    laps_csv: Path = config.LAPS_CSV,
    meta_json: Path = config.META_JSON,
    output_path: Path = config.OUTPUT_VIDEO,
    fps: int = 24,
    frames_per_lap: int = 5,
    width: int = 1280,
    height: int = 720,
) -> Path:
    df, meta = load_data(laps_csv, meta_json)
    timelapse = RaceTimelapse(
        df, meta, fps=fps, frames_per_lap=frames_per_lap, width=width, height=height
    )
    return timelapse.render(output_path)


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render the F1 race timelapse MP4.")
    p.add_argument("--output", type=Path, default=config.OUTPUT_VIDEO)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--frames-per-lap", type=int, default=5, dest="frames_per_lap")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    return p.parse_args(argv)


def main(argv=None) -> None:
    args = _parse_args(argv)
    animate(
        output_path=args.output, fps=args.fps, frames_per_lap=args.frames_per_lap,
        width=args.width, height=args.height,
    )


if __name__ == "__main__":
    main()
