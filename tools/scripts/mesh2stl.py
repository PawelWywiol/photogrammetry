#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["trimesh>=4.5", "numpy", "networkx", "rtree", "shapely"]
# ///
"""Convert a reconstructed mesh (OBJ/PLY/GLB/USDZ-exported OBJ) to a print-ready STL.

Object Capture emits metres. Slicers read STL as millimetres, so the default
scale of 1000 maps 1 m -> 1000 mm and yields a physically correct model *if*
Object Capture recovered true scale. When it did not, pass --target-size to
scale the longest bounding-box edge to a measured real-world dimension.
"""

import argparse
import sys

import numpy as np
import trimesh


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--scale", type=float, default=1000.0,
                        help="multiplier applied to source units (default 1000: metres -> mm)")
    parser.add_argument("--target-size", type=float,
                        help="scale so the longest bounding-box edge equals this many mm (overrides --scale)")
    parser.add_argument("--no-repair", action="store_true", help="skip hole filling and normal fixing")
    parser.add_argument("--ascii", dest="binary", action="store_false", help="write ASCII STL")
    parser.set_defaults(binary=True)
    return parser.parse_args()


def report(mesh: trimesh.Trimesh, label: str) -> None:
    extents = mesh.extents
    print(f"[mesh2stl] {label}: {len(mesh.faces)} faces, "
          f"bbox {extents[0]:.2f} x {extents[1]:.2f} x {extents[2]:.2f}, "
          f"watertight={mesh.is_watertight}, volume={mesh.volume if mesh.is_watertight else float('nan'):.2f}")


def main() -> int:
    args = parse_args()

    loaded = trimesh.load(args.input, force="mesh", process=True)
    if not isinstance(loaded, trimesh.Trimesh) or loaded.is_empty:
        print(f"[mesh2stl] error: no usable geometry in {args.input}", file=sys.stderr)
        return 1
    mesh: trimesh.Trimesh = loaded
    # OBJ duplicates vertices along UV seams, which makes a closed surface look full of
    # holes. Merge across texture/normal splits so the watertight check means something.
    mesh.merge_vertices(merge_tex=True, merge_norm=True)
    report(mesh, "loaded")

    scale = args.scale
    if args.target_size:
        longest = float(np.max(mesh.extents))
        if longest <= 0:
            print("[mesh2stl] error: degenerate bounding box", file=sys.stderr)
            return 1
        scale = args.target_size / longest
        print(f"[mesh2stl] --target-size {args.target_size}mm -> scale {scale:.4f}")
    mesh.apply_scale(scale)

    if not args.no_repair:
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        trimesh.repair.fix_winding(mesh)
        trimesh.repair.fix_normals(mesh)
        trimesh.repair.fill_holes(mesh)

    mesh.apply_translation(-mesh.bounds[0])  # rest the model on Z=0 at the origin
    report(mesh, "written")
    if not mesh.is_watertight:
        print("[mesh2stl] WARNING: mesh is not watertight — repair it in your slicer "
              "or a mesh editor before printing", file=sys.stderr)

    mesh.export(args.output, file_type="stl_ascii" if not args.binary else "stl")
    print(f"[mesh2stl] wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
