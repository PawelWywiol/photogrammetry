#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pymeshlab", "numpy"]
# ///
"""Clean up and optimise a reconstructed mesh before printing.

Read this first: none of these operations can invent geometry that the reconstruction
never captured. If the subject moved during the shoot, the detail is simply not in the
data — see docs/07-moving-subjects.md. What this script does is remove reconstruction
noise, make the triangulation uniform, close holes and bring out the detail that *is*
present. That is worth doing, and it is not the same as recovering lost detail.

Operations run in a fixed, deliberate order:
  clean -> weld -> poisson -> smooth -> sharpen -> remesh -> decimate -> close holes
"""

import argparse
import sys

import numpy as np
import pymeshlab as ml

# Preset distances are expressed as multiples of the mesh's own mean edge length, so a
# preset behaves the same whether the model is scaled in metres or millimetres.
PRESETS = {
    # Reconstruction noise removal without losing shape. The everyday choice.
    "print": dict(weld_rel=0.25, smooth="taubin", smooth_iters=6, remesh_rel=1.0,
                  close_holes=True),
    # Same, plus geometric unsharp masking to lift the detail that survived.
    "detail": dict(weld_rel=0.25, smooth="taubin", smooth_iters=3, sharpen=0.6,
                   remesh_rel=0.85, close_holes=True),
    # Heavier denoise for meshes wrecked by a moving subject: accept a smooth,
    # sculpture-like surface instead of a lumpy one.
    "denoise": dict(weld_rel=0.5, smooth="hc", smooth_iters=3, poisson=9,
                    remesh_rel=1.0, close_holes=True),
    # Smallest sane file for slicing, shape preserved.
    "light": dict(weld_rel=0.5, smooth="taubin", smooth_iters=4, decimate=60000,
                  close_holes=True),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--preset", choices=sorted(PRESETS),
                        help=f"named recipe: {', '.join(sorted(PRESETS))}")
    parser.add_argument("--weld", type=float, metavar="MM",
                        help="merge vertices closer than this (removes reconstruction seams)")
    parser.add_argument("--smooth", choices=["taubin", "hc", "laplacian"],
                        help="taubin = denoise without shrinking (recommended); "
                             "hc = volume-preserving; laplacian = strongest, shrinks")
    parser.add_argument("--smooth-iters", type=int, default=6)
    parser.add_argument("--sharpen", type=float, metavar="W",
                        help="geometric unsharp mask weight, e.g. 0.6 — enhances existing detail")
    parser.add_argument("--remesh", type=float, metavar="MM",
                        help="isotropic remesh to this target edge length (uniform triangles)")
    parser.add_argument("--decimate", type=int, metavar="FACES",
                        help="reduce to this face count, preserving shape")
    parser.add_argument("--poisson", type=int, metavar="DEPTH",
                        help="rebuild the surface with screened Poisson (8-10); "
                             "guarantees a closed, uniform surface but rounds off sharp features")
    parser.add_argument("--close-holes", action="store_true")
    parser.add_argument("--max-hole-size", type=int, default=1000)
    return parser.parse_args()


def settings(args: argparse.Namespace) -> dict:
    values = dict(PRESETS[args.preset]) if args.preset else {}
    for key in ("weld", "smooth", "sharpen", "remesh", "decimate", "poisson"):
        if getattr(args, key) is not None:
            values[key] = getattr(args, key)
    if args.close_holes:
        values["close_holes"] = True
    if args.smooth and args.smooth_iters:
        values["smooth_iters"] = args.smooth_iters
    return values


def mean_edge_length(mesh_set: ml.MeshSet) -> float:
    """Average triangle edge, derived from surface area — a scale-free handle on how dense
    the mesh already is, so presets do not need to know the model's units."""
    mesh = mesh_set.current_mesh()
    area = mesh_set.get_geometric_measures().get("surface_area", 0.0)
    faces = max(mesh.face_number(), 1)
    # area of an equilateral triangle = (sqrt(3)/4) * edge^2
    return float(np.sqrt(4.0 * (area / faces) / np.sqrt(3.0)))


def stats(mesh_set: ml.MeshSet, label: str) -> dict:
    mesh = mesh_set.current_mesh()
    measures = mesh_set.get_geometric_measures()
    bbox = mesh.bounding_box()
    extents = np.array([bbox.dim_x(), bbox.dim_y(), bbox.dim_z()])
    report = {
        "faces": mesh.face_number(),
        "vertices": mesh.vertex_number(),
        "area": measures.get("surface_area", float("nan")),
        "volume": measures.get("mesh_volume", float("nan")),
        "bbox": extents,
    }
    print(f"[meshopt] {label:9s} {report['faces']:>8d} faces  {report['vertices']:>8d} verts  "
          f"bbox {extents[0]:.1f} x {extents[1]:.1f} x {extents[2]:.1f}  "
          f"area {report['area']:.0f}  volume {report['volume']:.0f}")
    return report


def main() -> int:
    args = parse_args()
    config = settings(args)
    if not config:
        print("error: nothing to do — pass --preset or at least one operation", file=sys.stderr)
        return 1

    mesh_set = ml.MeshSet()
    mesh_set.load_new_mesh(args.input)
    before = stats(mesh_set, "input")
    edge = mean_edge_length(mesh_set)
    print(f"[meshopt] mean edge length: {edge:.3f}")

    mesh_set.meshing_remove_duplicate_vertices()
    mesh_set.meshing_remove_duplicate_faces()
    mesh_set.meshing_remove_unreferenced_vertices()

    # Resolve relative preset distances against this mesh's own density.
    for key in ("weld", "remesh"):
        if f"{key}_rel" in config and key not in config:
            config[key] = config.pop(f"{key}_rel") * edge

    if "weld" in config:
        # PercentageValue is relative to the bounding-box diagonal; we want absolute units.
        diagonal = float(np.linalg.norm(before["bbox"]))
        percent = 100.0 * config["weld"] / diagonal
        print(f"[meshopt] weld: merging vertices closer than {config['weld']:.3f} ({percent:.4f}%)")
        mesh_set.meshing_merge_close_vertices(threshold=ml.PercentageValue(percent))
        stats(mesh_set, "welded")

    if "poisson" in config:
        depth = int(config["poisson"])
        print(f"[meshopt] poisson: rebuilding surface at depth {depth}")
        mesh_set.compute_normal_for_point_clouds() if mesh_set.current_mesh().face_number() == 0 else None
        mesh_set.generate_surface_reconstruction_screened_poisson(depth=depth, preclean=True)
        stats(mesh_set, "poisson")

    if "smooth" in config:
        iterations = int(config.get("smooth_iters", 6))
        kind = config["smooth"]
        print(f"[meshopt] smooth: {kind} x{iterations}")
        if kind == "taubin":
            mesh_set.apply_coord_taubin_smoothing(stepsmoothnum=iterations)
        elif kind == "hc":
            for _ in range(iterations):
                mesh_set.apply_coord_hc_laplacian_smoothing()
        else:
            mesh_set.apply_coord_laplacian_smoothing(stepsmoothnum=iterations)
        stats(mesh_set, "smoothed")

    if "sharpen" in config:
        weight = float(config["sharpen"])
        print(f"[meshopt] sharpen: geometric unsharp mask weight {weight}")
        mesh_set.apply_coord_unsharp_mask(weight=weight)
        stats(mesh_set, "sharpened")

    if "remesh" in config:
        target = float(config["remesh"])
        diagonal = float(np.linalg.norm(before["bbox"]))
        percent = 100.0 * target / diagonal
        print(f"[meshopt] remesh: isotropic, target edge {target:.3f} ({percent:.4f}%)")
        mesh_set.meshing_isotropic_explicit_remeshing(
            targetlen=ml.PercentageValue(percent), iterations=6, adaptive=True)
        stats(mesh_set, "remeshed")

    if "decimate" in config:
        target = int(config["decimate"])
        print(f"[meshopt] decimate: to {target} faces")
        mesh_set.meshing_decimation_quadric_edge_collapse(
            targetfacenum=target, preservenormal=True, preserveboundary=True,
            planarquadric=True, autoclean=True)
        stats(mesh_set, "decimated")

    if config.get("close_holes"):
        try:
            mesh_set.meshing_close_holes(maxholesize=args.max_hole_size, selfintersection=False)
            stats(mesh_set, "closed")
        except Exception as error:  # a mesh with no holes makes the filter throw
            print(f"[meshopt] close holes skipped: {error}")

    mesh_set.save_current_mesh(args.output)
    after = stats(mesh_set, "output")
    print(f"[meshopt] faces {before['faces']} -> {after['faces']} "
          f"({100.0 * after['faces'] / max(before['faces'], 1):.0f}%), wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
