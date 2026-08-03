#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "pillow-heif", "numpy"]
# ///
"""Audit an images/ folder before spending minutes on a reconstruction.

Checks the three things that actually decide whether a photogrammetry run can succeed:
real file format (not the extension), image sharpness, and how long the shoot took —
because a long shoot means a live subject had time to move, and photogrammetry needs a
rigid subject.
"""

import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()
Image.MAX_IMAGE_PIXELS = None

MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png"}


def real_format(path: Path) -> str:
    head = path.read_bytes()[:16]
    for magic, name in MAGIC.items():
        if head.startswith(magic):
            return name
    return "heic" if head[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1", b"ftypmsf1") else ""


def sharpness(image: Image.Image) -> float:
    """Variance of the Laplacian on a fixed-height grayscale copy — the standard blur metric.
    Resizing to a fixed size keeps the numbers comparable across resolutions."""
    grey = np.asarray(image.convert("L").resize((768, 768))).astype(np.float32)
    lap = (-4 * grey
           + np.roll(grey, 1, 0) + np.roll(grey, -1, 0)
           + np.roll(grey, 1, 1) + np.roll(grey, -1, 1))[1:-1, 1:-1]
    return float(lap.var())


def capture_time(image: Image.Image) -> datetime | None:
    exif = image.getexif()
    raw = exif.get(306) or exif.get_ifd(0x8769).get(36867)
    try:
        return datetime.strptime(raw, "%Y:%m:%d %H:%M:%S") if raw else None
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images_dir")
    parser.add_argument("--blur-ratio", type=float, default=0.4,
                        help="flag images below this fraction of the median sharpness")
    args = parser.parse_args()

    paths = sorted(p for p in Path(args.images_dir).iterdir()
                   if p.is_file() and not p.name.startswith(".") and p.suffix != ".bak")
    if not paths:
        print(f"error: no files in {args.images_dir}", file=sys.stderr)
        return 1

    formats, sizes, mismatched, unsupported, scores, times = Counter(), Counter(), [], [], [], []
    for path in paths:
        actual = real_format(path)
        if not actual:
            unsupported.append(path.name)
            continue
        formats[actual] += 1
        declared = path.suffix.lower().lstrip(".").replace("jpeg", "jpg")
        if declared != actual:
            mismatched.append(path.name)
        with Image.open(path) as image:
            sizes[f"{image.width}x{image.height}"] += 1
            scores.append((sharpness(image), path.name))
            when = capture_time(image)
        if when:
            times.append(when)

    total = len(paths) - len(unsupported)
    print(f"images:      {total}")
    print(f"formats:     {dict(formats)}")
    print(f"resolutions: {dict(sizes)}")

    warnings = []
    if unsupported:
        print(f"unsupported: {len(unsupported)} -> {unsupported[:5]}")
        return 1
    if mismatched:
        print(f"extension mismatches: {len(mismatched)} (handled by 'pg prep')")
    if len(sizes) > 1:
        warnings.append("mixed resolutions — crops or edits break camera calibration")

    values = np.array([s for s, _ in scores])
    median = float(np.median(values))
    blurry = sorted(n for s, n in scores if s < median * args.blur_ratio)
    print(f"sharpness:   median {median:.0f}, range {values.min():.0f}–{values.max():.0f}")
    if blurry:
        print(f"             {len(blurry)} soft/blurry: {blurry[:6]}")
        warnings.append(f"{len(blurry)} blurry images — delete them, they add noise not detail")

    if len(times) >= 2:
        span = (max(times) - min(times)).total_seconds()
        print(f"shoot span:  {span:.0f}s for {len(times)} images ({span / max(len(times) - 1, 1):.1f}s apart)")
        if span > 120:
            warnings.append(
                f"shoot took {span:.0f}s — anything alive (person, pet) will have moved. "
                "Photogrammetry needs a rigid subject; use 'pg frames' on a video instead")

    if total < 20:
        warnings.append(f"only {total} images — expect a poor reconstruction (aim for 100+)")
    elif total < 80:
        warnings.append(f"{total} images is thin — Apple recommends 100+ for a good result")
    if total > 1000:
        print("error: over the 1000-image PhotogrammetrySession limit", file=sys.stderr)
        return 1

    for warning in warnings:
        print(f"WARNING: {warning}")
    print("ok" if not warnings else "ok (with warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
