#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy"]
# ///
"""Extract the sharpest frames from a video into an images/ folder.

This is the answer to subjects that will not hold still. A 20-second orbit shot as video
gives a subject no time to move, and picking the sharpest frame out of each time slice
beats any still sequence a person can shoot by hand.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


def sharpness(path: Path) -> float:
    with Image.open(path) as image:
        grey = np.asarray(image.convert("L").resize((768, 768))).astype(np.float32)
    lap = (-4 * grey
           + np.roll(grey, 1, 0) + np.roll(grey, -1, 0)
           + np.roll(grey, 1, 1) + np.roll(grey, -1, 1))[1:-1, 1:-1]
    return float(lap.var())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video")
    parser.add_argument("output_dir", help="destination images/ folder (must be empty or new)")
    parser.add_argument("--count", type=int, default=150, help="frames to keep (default 150)")
    parser.add_argument("--candidates-per-frame", type=int, default=4,
                        help="frames sampled per kept frame, to choose the sharpest (default 4)")
    parser.add_argument("--prefix", default="frame")
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        print("error: ffmpeg not found — brew install ffmpeg", file=sys.stderr)
        return 1
    if args.count > 1000:
        print("error: PhotogrammetrySession accepts at most 1000 images", file=sys.stderr)
        return 1

    output = Path(args.output_dir)
    if output.exists() and any(output.iterdir()):
        print(f"error: {output} is not empty", file=sys.stderr)
        return 1
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        wanted = args.count * args.candidates_per_frame
        duration = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", args.video],
            capture_output=True, text=True, check=True).stdout.strip())
        fps = wanted / duration
        print(f"[frames] {duration:.1f}s video -> sampling {wanted} candidates at {fps:.1f} fps")

        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", args.video,
             "-vf", f"fps={fps:.4f}", "-q:v", "2", f"{tmp}/cand_%05d.jpg"],
            check=True)

        candidates = sorted(Path(tmp).glob("cand_*.jpg"))
        if not candidates:
            print("error: ffmpeg produced no frames", file=sys.stderr)
            return 1
        print(f"[frames] scoring {len(candidates)} candidates")

        scored = [(sharpness(p), p) for p in candidates]
        # One winner per time slice keeps coverage even; picking the sharpest inside the
        # slice drops motion blur without leaving a gap in the orbit.
        buckets = np.array_split(np.arange(len(scored)), min(args.count, len(scored)))
        kept = [max((scored[i] for i in bucket), key=lambda item: item[0])
                for bucket in buckets if len(bucket)]

        for index, (score, path) in enumerate(kept, start=1):
            shutil.copy2(path, output / f"{args.prefix}_{index:04d}.jpg")

        values = np.array([s for s, _ in kept])
        print(f"[frames] kept {len(kept)} frames in {output}")
        print(f"[frames] sharpness median {np.median(values):.0f}, "
              f"range {values.min():.0f}–{values.max():.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
