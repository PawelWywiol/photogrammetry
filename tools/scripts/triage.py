#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "pillow-heif", "numpy"]
# ///
"""Find which photos are hurting the reconstruction, using the solver's own camera poses.

Sharpness alone is a bad guide — a soft frame shot from close up can carry more usable
surface than a crisp one shot from far away, and deleting a run of consecutive frames tears
a hole in the orbit that costs far more than the blur did. This tool reads the camera poses
that Object Capture actually recovered and judges each photo on four things:

  1. did the solver manage to place it at all
  2. where it sits on the orbit, and whether dropping it would open an angular gap
  3. how far it was from the subject compared with the rest of the shoot
  4. how sharp it is

Only a photo that is weak on quality *and* redundant in coverage is worth deleting.

Generate the input with:  objcap <prepared-dir> <out.json>
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()
Image.MAX_IMAGE_PIXELS = None


def sharpness(path: Path) -> float:
    with Image.open(path) as image:
        grey = np.asarray(image.convert("L").resize((768, 768))).astype(np.float32)
    lap = (-4 * grey
           + np.roll(grey, 1, 0) + np.roll(grey, -1, 0)
           + np.roll(grey, 1, 1) + np.roll(grey, -1, 1))[1:-1, 1:-1]
    return float(lap.var())


def robust_scale(values: np.ndarray) -> float:
    return float(np.median(np.abs(values - np.median(values)))) or 1e-9


def gaps_around(azimuths: np.ndarray) -> np.ndarray:
    """Angular gap that each frame is responsible for: distance to its two orbit neighbours."""
    order = np.argsort(azimuths)
    ordered = azimuths[order]
    forward = np.diff(np.concatenate([ordered, [ordered[0] + 360.0]]))
    result = np.empty_like(azimuths)
    result[order] = forward
    return result


def merged_gap_without(azimuths: np.ndarray, index: int) -> float:
    """Gap left behind if this one frame goes: its own forward gap plus its predecessor's.
    Only the local hole matters — a wide gap elsewhere on the orbit is not this frame's fault."""
    order = np.argsort(azimuths)
    position = int(np.where(order == index)[0][0])
    forward = gaps_around(azimuths)
    previous = order[position - 1]
    return float(forward[previous] + forward[index])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("poses_json")
    parser.add_argument("images_dir")
    parser.add_argument("--max-gap", type=float, default=15.0,
                        help="never open an orbit gap wider than this, in degrees (default 15)")
    parser.add_argument("--blur-ratio", type=float, default=0.5,
                        help="a frame counts as soft below this fraction of the median sharpness")
    parser.add_argument("--write-subset", metavar="DIR",
                        help="write a symlink farm of the keepers, ready for objcap")
    parser.add_argument("--verbose", action="store_true", help="print every frame, not just flagged ones")
    args = parser.parse_args()

    poses = json.load(open(args.poses_json))["poses"]
    if not poses:
        print("error: no poses in the json — the solver aligned nothing", file=sys.stderr)
        return 1

    images = {p.name: p for p in Path(args.images_dir).iterdir()
              if p.is_file() and not p.name.startswith(".")}
    # objcap sees the .prepared symlinks, whose extensions may differ from the originals.
    by_stem = {Path(name).stem: path for name, path in images.items()}

    placed = {Path(p["file"]).stem for p in poses}
    unregistered = sorted(stem for stem in by_stem if stem not in placed)

    translations = np.array([p["translation"] for p in poses], dtype=float)
    stems = [Path(p["file"]).stem for p in poses]
    centre = translations.mean(axis=0)
    relative = translations - centre

    # Object Capture's world is Y-up, so the orbit lives in the XZ plane.
    azimuth = np.degrees(np.arctan2(relative[:, 2], relative[:, 0])) % 360.0
    radius = np.linalg.norm(relative[:, [0, 2]], axis=1)
    height = relative[:, 1]
    sharp = np.array([sharpness(by_stem[s]) for s in stems])

    print(f"registered:  {len(poses)} of {len(by_stem)} photos")
    if unregistered:
        print(f"NOT PLACED:  {len(unregistered)} -> {unregistered}")
        print("             the solver could not position these at all; they contribute nothing")

    gap = gaps_around(azimuth)
    covered = 360.0 - float(np.sum(gap[gap > args.max_gap] - args.max_gap))
    print(f"orbit:       median step {np.median(gap):.1f}deg, "
          f"largest gap {gap.max():.1f}deg, effective coverage ~{covered:.0f}deg")
    print(f"distance:    median {np.median(radius):.2f}, "
          f"range {radius.min():.2f}-{radius.max():.2f} (solver units)")
    print(f"height:      spread {height.std():.2f}")

    # A shoot done at two clearly different distances splits into two rings. That is worth
    # naming, because the close ring carries most of the resolution.
    near = radius < np.median(radius) * 0.7
    if near.sum() >= 3:
        print(f"NOTE:        {near.sum()} photos were taken much closer than the rest "
              f"({radius[near].mean():.2f} vs {radius[~near].mean():.2f}). "
              "Those carry the most detail — do not delete them for being soft.")

    median_sharp = float(np.median(sharp))
    soft = sharp < median_sharp * args.blur_ratio
    far = radius > np.median(radius) + 3 * robust_scale(radius)
    # Close-range frames are softer simply because hand shake shows more at short range,
    # yet they carry the most pixels on the subject. Deleting them measurably wrecked a
    # reconstruction here (docs/05-gotchas.md), so softness alone never condemns them.
    soft = soft & ~near

    print(f"\n{'photo':<16}{'azim':>7}{'gap':>7}{'dist':>7}{'sharp':>8}  verdict")
    droppable: list[int] = []
    for i in np.argsort(azimuth):
        reasons = []
        if soft[i]:
            reasons.append("soft")
        if far[i]:
            reasons.append("distant")
        # Redundant only if the orbit survives losing it.
        merged = merged_gap_without(azimuth, i)
        verdict = ""
        if reasons and merged <= args.max_gap:
            verdict = f"DROP ({'+'.join(reasons)}, leaves only a {merged:.0f}deg gap)"
            droppable.append(i)
        elif reasons:
            verdict = f"keep ({'+'.join(reasons)}, but removing it opens a {merged:.0f}deg gap)"
        if verdict or args.verbose:
            print(f"{stems[i]:<16}{azimuth[i]:>7.1f}{gap[i]:>7.1f}{radius[i]:>7.2f}"
                  f"{sharp[i]:>8.0f}  {verdict}")

    print()
    if unregistered:
        print(f"remove outright ({len(unregistered)}): {unregistered}")
    if droppable:
        print(f"safe to drop ({len(droppable)}): {sorted(stems[i] for i in droppable)}")
    else:
        print("safe to drop: none — every weak frame is holding the orbit together.")
    print("Everything else is load-bearing. Deleting consecutive frames tears the orbit; "
          "check the azim column before removing anything by hand.")

    if args.write_subset:
        keep = [i for i in range(len(stems)) if i not in droppable]
        out = Path(args.write_subset)
        out.mkdir(parents=True, exist_ok=True)
        if any(out.iterdir()):
            print(f"error: {out} is not empty", file=sys.stderr)
            return 1
        for i in keep:
            source = by_stem[stems[i]].resolve()
            (out / f"{stems[i]}.jpg").symlink_to(source)
        print(f"\nwrote {len(keep)} keepers to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
