"""Stitch the two race animations into one synced video per Grand Prix.

Renders the position-battle race (``race_animator``) and the position-by-lap
timeline (``animator``) with **matched timing** — same ``fps`` and
``frames_per_lap``, so both share an identical frame->lap clock — then uses
ffmpeg to place them side by side (or stacked) into a single MP4. Because the
clocks match, lap *N* lands on the same frame in both panels: they stay in sync.

    python combine_gp_videos.py                 # side-by-side -> latest_race_combined.mp4
    python combine_gp_videos.py --layout stack  # timeline under the race
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("combine")

DIVIDER = 6  # px separator between the two panels
DIVIDER_COLOR = "0x1B1B22"


def _ffmpeg_bin() -> str:
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _stack_filter(layout: str) -> str:
    """ffmpeg filtergraph: pad a divider onto input 0, then h/v-stack with input 1."""
    if layout == "stack":  # timeline below the race (each full width)
        pad = f"[0:v]pad=iw:ih+{DIVIDER}:0:0:{DIVIDER_COLOR}[a]"
        return f"{pad};[a][1:v]vstack=inputs=2[v]"
    # side by side (default): race left, timeline right
    pad = f"[0:v]pad=iw+{DIVIDER}:ih:0:0:{DIVIDER_COLOR}[a]"
    return f"{pad};[a][1:v]hstack=inputs=2[v]"


def stack_videos(
    replay_path: Path,
    timeline_path: Path,
    output_path: Path = config.OUTPUT_COMBINED,
    layout: str = "side",
    bitrate: str = "6500k",
) -> Path:
    """ffmpeg-stitch two already-rendered panels into one MP4.

    The panels must have been rendered with matching ``fps`` and
    ``frames_per_lap`` so their frame->lap clocks line up.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _ffmpeg_bin(), "-y", "-loglevel", "error",
        "-i", str(replay_path), "-i", str(timeline_path),
        "-filter_complex", _stack_filter(layout), "-map", "[v]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-b:v", bitrate,
        str(output_path),
    ]
    log.info("Stitching panels (%s) -> %s", layout, output_path)
    subprocess.run(cmd, check=True)
    log.info("Saved %s", output_path)
    return output_path


def combine(
    output_path: Path = config.OUTPUT_COMBINED,
    fps: int = 24,
    frames_per_lap: int = 6,
    layout: str = "side",
    width: int = 1280,
    height: int = 720,
    bitrate: str = "6500k",
) -> Path:
    """Render both panels with matched timing, then stitch them together."""
    import animator
    import race_animator

    with tempfile.TemporaryDirectory() as tmp:
        replay = Path(tmp) / "replay.mp4"
        timeline = Path(tmp) / "timeline.mp4"

        # Matched fps + frames_per_lap => identical frame counts => perfect sync.
        log.info("Rendering position-battle race panel ...")
        race_animator.animate(output_path=replay, fps=fps, frames_per_lap=frames_per_lap,
                              width=width, height=height)
        log.info("Rendering position-by-lap timeline panel ...")
        animator.animate(output_path=timeline, fps=fps, frames_per_lap=frames_per_lap,
                         width=width, height=height)

        return stack_videos(replay, timeline, output_path, layout=layout, bitrate=bitrate)


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="Combine both race videos into one synced MP4.")
    p.add_argument("--output", type=Path, default=config.OUTPUT_COMBINED)
    p.add_argument("--layout", choices=["side", "stack"], default="side",
                   help="side = panels left/right (default); stack = timeline below the race.")
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--frames-per-lap", type=int, default=6, dest="frames_per_lap")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    combine(output_path=args.output, fps=args.fps, frames_per_lap=args.frames_per_lap,
            layout=args.layout, width=args.width, height=args.height)


if __name__ == "__main__":
    main()
