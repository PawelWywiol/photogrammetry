#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["trimesh>=4.5", "numpy", "pillow", "scipy"]
# ///
"""Render shaded views of a mesh to a PNG, headless.

Point-splat renderer: projects vertices with an orthographic camera, resolves visibility
with a z-buffer and shades from vertex normals. No OpenGL, no display, and fast enough for
multi-million-vertex meshes — which is exactly where the GUI-free options give up.
Geometry only; textures are ignored on purpose, since print quality lives in the mesh.
"""

import argparse
import sys

import numpy as np
import trimesh
from PIL import Image


def rotation(azimuth_deg: float, elevation_deg: float) -> np.ndarray:
    az, el = np.radians(azimuth_deg), np.radians(elevation_deg)
    ry = np.array([[np.cos(az), 0, np.sin(az)], [0, 1, 0], [-np.sin(az), 0, np.cos(az)]])
    rx = np.array([[1, 0, 0], [0, np.cos(el), -np.sin(el)], [0, np.sin(el), np.cos(el)]])
    return rx @ ry


def render(mesh: trimesh.Trimesh, azimuth: float, elevation: float, size: int) -> np.ndarray:
    rot = rotation(azimuth, elevation)
    points = (mesh.vertices - mesh.centroid) @ rot.T
    normals = np.asarray(mesh.vertex_normals) @ rot.T

    span = points[:, :2].max(axis=0) - points[:, :2].min(axis=0)
    scale = (size * 0.88) / max(span.max(), 1e-9)
    px = np.clip((points[:, 0] * scale + size / 2).astype(np.int32), 0, size - 1)
    py = np.clip((-points[:, 1] * scale + size / 2).astype(np.int32), 0, size - 1)
    flat = py * size + px

    # Keep the nearest vertex per pixel: sort back-to-front, then let later writes win.
    order = np.argsort(-points[:, 2], kind="stable")
    index = np.full(size * size, -1, dtype=np.int64)
    index[flat[order]] = order

    light = np.array([0.4, 0.6, 0.7])
    light /= np.linalg.norm(light)
    lambert = np.clip(normals @ light, 0, 1)
    shade = 0.18 + 0.82 * lambert ** 0.75

    image = np.zeros(size * size, dtype=np.float32)
    hit = index >= 0
    image[hit] = shade[index[hit]]

    # Splat once into 4-neighbours so sparse meshes render solid instead of speckled.
    grid = image.reshape(size, size)
    filled = grid.copy()
    for shift, axis in ((1, 0), (-1, 0), (1, 1), (-1, 1)):
        filled = np.maximum(filled, np.roll(grid, shift, axis=axis))
    grid = np.where(grid > 0, grid, filled)

    return (np.clip(grid, 0, 1) * 255).astype(np.uint8)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--views", default="0,90,180,270",
                        help="comma-separated azimuths in degrees (default: 0,90,180,270)")
    parser.add_argument("--elevation", type=float, default=20.0)
    parser.add_argument("--size", type=int, default=700, help="pixels per view")
    args = parser.parse_args()

    mesh = trimesh.load(args.input, force="mesh", process=False)
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        print(f"[meshview] error: no usable geometry in {args.input}", file=sys.stderr)
        return 1
    print(f"[meshview] {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")

    azimuths = [float(a) for a in args.views.split(",")]
    tiles = [render(mesh, az, args.elevation, args.size) for az in azimuths]
    Image.fromarray(np.hstack(tiles)).save(args.output)
    print(f"[meshview] wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
