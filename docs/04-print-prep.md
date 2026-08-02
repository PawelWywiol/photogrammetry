# Print preparation

## Units and scale — read this first

- Object Capture emits geometry in **metres**.
- STL has **no unit field**. Every slicer reads STL numbers as **millimetres**.
- `mesh2stl.py` therefore multiplies by **1000** by default, so 1 m → 1000 mm.

That conversion is arithmetically correct. Whether the result is *physically* correct is a
separate question: **Object Capture estimates real-world scale from the photos, and that
estimate is often wrong** when the input is ordinary Camera-app photos with no depth data.
(Photos taken through Apple's own Object Capture *iOS app* embed LiDAR/depth auxiliary data
and scale much better — plain Camera-app shots do not.)

**So always verify.** Measure one real dimension of the object with a ruler, compare it to
the bounding box `mesh2stl.py` prints, and if it is off, rescale:

```bash
# force the longest bounding-box edge to a measured 240 mm
./bin/pg stl my-object --target-size 240

# or apply a known correction factor instead of the default 1000
./bin/pg stl my-object --scale 620
```

Record the measured dimension in `projects/<name>/NOTES.md` so the next run is not a guess.

A scale bar of known length placed next to the object during the shoot makes this
trivial — you can measure it in the model and derive the factor exactly.

## Watertightness

`mesh2stl.py` reports `watertight=True/False`. A non-watertight (open) mesh has holes;
slicers may still print it, but results are unpredictable.

**A false alarm to know about:** an OBJ duplicates vertices along UV texture seams, which
makes a perfectly closed surface *look* full of holes. `mesh2stl.py` merges those split
vertices before checking, so its report is meaningful. If you check the OBJ in another tool
and it says "not watertight", merge vertices by distance first.

Real holes usually come from:

- **The unseen underside.** Expected — the object was sitting on a surface. Often fine: the
  script fills the hole, or you cut a flat base in the slicer anyway.
- **Missing coverage.** A height band you forgot to shoot. Fix it by shooting more photos,
  not by patching the mesh.

`mesh2stl.py` runs a repair pass by default: drops degenerate faces, fixes winding and
normals, fills holes. Disable with `--no-repair` if you want the raw mesh.

## Polygon count

`full` detail gives roughly 100 k faces, which slices fine. Reduce only if your slicer
struggles or you want a lighter file:

```bash
./bin/pg build my-object --polygons 150000
```

Reducing polygons is a reconstruction-time choice — cheaper and better than decimating
afterwards, because the solver keeps detail where it matters.

## Orientation and position

`mesh2stl.py` translates the mesh so its bounding box rests at the origin with the minimum
corner at `(0,0,0)` — it lands on the build plate instead of floating or sinking. It does
**not** rotate anything. Choose the print orientation in your slicer, where you can see
supports and layer direction.

## Slicer checklist

1. Import the STL, confirm the dimensions match your measurement.
2. Run the slicer's mesh repair (PrusaSlicer: *Fix through Netfabb* / *Repair*;
   Bambu Studio and Orca have equivalents).
3. Orient to minimise supports and put fine detail on upward-facing surfaces.
4. Flat base? Cut with a plane rather than relying on the reconstructed underside.
5. Photogrammetry surfaces are noisy at sub-millimetre scale — do not expect a 0.05 mm
   layer height to reveal real detail that the photos never captured.

## Colour printing

STL carries geometry only. For a colour-capable workflow keep `output/model/*.obj` plus its
`.mtl` and texture PNGs, or export a USDZ/glTF instead.
