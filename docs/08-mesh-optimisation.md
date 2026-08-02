# Mesh optimisation

`pg opt` (`tools/scripts/meshopt.py`, built on PyMeshLab) cleans up a reconstructed mesh:
merges near-duplicate vertices, removes reconstruction noise, makes the triangulation
uniform, closes holes and can enhance the detail that is present.

```bash
make my-object opt              # 'print' preset -> output/my-object-print.stl
make my-object opt detail
make my-object opt denoise
make my-object opt light

./bin/pg opt my-object --weld 0.5 --smooth taubin --remesh 2.5   # individual operations
```

Output is named after the preset, so variants sit side by side and you can compare them
before deciding what to slice.

## What this can and cannot do

**It cannot add detail that the reconstruction never captured.** If the subject moved
during the shoot, the geometry is gone and no filter recovers it —
[07-moving-subjects.md](07-moving-subjects.md) explains why. Optimisation makes the surface
*cleaner*, *more printable* and *more even*; it does not make it more faithful to the
original object.

What it genuinely fixes:

- **Vertex noise** from the reconstruction — visible as a grainy, pitted surface.
- **Uneven triangulation** — photogrammetry meshes have dense patches and sparse patches;
  slicers and supports behave better on uniform triangles.
- **Redundant vertices** — merging near-coincident vertices cuts file size with no shape cost.
- **Small holes**.
- **Weak feature definition** — geometric unsharp masking makes existing folds and edges
  read more strongly (`detail` preset).

## Presets

| Preset | What it does | Use when |
|---|---|---|
| `print` | weld, Taubin denoise, isotropic remesh, close holes | **Default.** Almost always the right choice |
| `detail` | as `print`, less smoothing, plus geometric unsharp mask | Soft, mushy surface where you want folds and edges to read |
| `denoise` | heavy weld, HC-Laplacian, screened Poisson rebuild | Lumpy mesh from a bad capture; accept a sculptural, smoothed look |
| `light` | weld, denoise, decimate to 60 k faces | Slicer struggles, or you want a small file |

Preset distances are expressed as multiples of the mesh's **own mean edge length**, so a
preset behaves identically whether the model is scaled in metres or millimetres.

## Measured on a real 97 152-face reconstruction (795 mm tall)

Deviation is measured against the unoptimised mesh with `get_hausdorff_distance`.

| Preset | Faces | Mean deviation | Max deviation | Watertight |
|---|---|---|---|---|
| original | 97 152 | — | — | yes |
| `print` | 93 410 | **0.054 mm** | 1.63 mm | yes |
| `light` | 60 000 | **0.051 mm** | 1.37 mm | yes |
| `detail` | 131 904 | 0.299 mm | 3.80 mm | yes |
| `denoise` | 89 112 | 0.305 mm | 13.03 mm | yes |

Read this as:

- `print` and `light` are **shape-faithful** — they clean up without moving the surface. On
  a 795 mm model, 0.05 mm mean deviation is far below what any printer resolves.
- `detail` deliberately exaggerates. That is the point of an unsharp mask; it is a stylistic
  choice, not a more accurate model.
- `denoise` rebuilds the surface with Poisson and moves it by up to 13 mm (1.6 % of the
  model). Use it when the input is bad enough that faithfulness is not the priority.

`light` deserves attention: **38 % fewer faces for the same shape fidelity as `print`**. If
file size matters, it costs nothing.

## Individual operations

| Flag | Effect |
|---|---|
| `--weld <mm>` | merge vertices closer than this (`meshing_merge_close_vertices`) |
| `--smooth taubin` | denoise **without shrinking** — λ/μ filtering. The safe default |
| `--smooth hc` | HC-Laplacian, volume preserving |
| `--smooth laplacian` | strongest denoise, visibly shrinks the model |
| `--smooth-iters <n>` | smoothing passes |
| `--sharpen <w>` | geometric unsharp mask; 0.3 subtle, 0.6 clear, >1 caricature |
| `--remesh <mm>` | isotropic remesh to a target edge length |
| `--decimate <faces>` | quadric edge-collapse decimation, shape preserving |
| `--poisson <depth>` | screened Poisson surface rebuild, 8–10 |
| `--close-holes` | fill holes up to `--max-hole-size` |

Operations always run in this order regardless of flag order:
**clean → weld → poisson → smooth → sharpen → remesh → decimate → close holes.**

## Why plain vertex merging is not enough on its own

Merging close vertices is a *topology* fix: it removes duplicates left along reconstruction
seams and reduces the vertex count. It does not change the surface, so on its own it will
not make a blobby model look better. It is step one of the pipeline, not the whole answer —
which is why the presets pair it with denoising and remeshing.

## Related

- Why the capture, not the mesh, is usually the problem: [07-moving-subjects.md](07-moving-subjects.md)
- Scale, watertightness, slicer hand-off: [04-print-prep.md](04-print-prep.md)
- Measured experiments and dead ends: [05-gotchas.md](05-gotchas.md)
