# Pipeline — from photos to STL

## Layout

```
projects/<name>/
  images/          ← you put photos here. Never written to by any script.
  NOTES.md         ← what the object is, how it was shot, its measured size
  .prepared/       ← generated: symlinks with truthful extensions
  .checkpoint/     ← generated: Object Capture working data, speeds up re-runs
  output/
    model/         ← generated: OBJ + MTL + USDA + texture maps
    <name>.stl     ← generated: print-ready mesh
```

Everything except `images/` and `NOTES.md` is disposable — delete and re-run.

## Steps

The `Makefile` wraps the common cases as `make <project> [action]` — `make my-object`,
`make my-object preview`, `make my-object check`. Everything below is what those targets
call, and what you use when you need the extra options.

```bash
# 0. drop photos into projects/<name>/images/
mkdir -p projects/my-object/images

# 1. validate the input
./bin/pg check my-object

# 2. reconstruct  (writes projects/my-object/output/model/)
./bin/pg build my-object --detail full

# 3. export a printable STL  (writes projects/my-object/output/my-object.stl)
./bin/pg stl my-object

# or the whole thing at once — adds the cleaned-up variants and a render
./bin/pg all my-object --detail full
```

`pg all` produces:

```
output/my-object.stl            raw reconstruction
output/my-object-print.stl      cleaned up, shape-faithful
output/my-object-light.stl      same shape, ~38% fewer faces
output/my-object-detail.stl     folds and edges enhanced
output/my-object-views.png      four rendered views
output/model/                   OBJ + USDA + texture maps
```

The first `pg build` compiles the `objcap` Swift binary automatically; later runs reuse it.

## Choosing a detail level

| `--detail` | Use it for | Typical faces | Time, 61 images, M2/16 GB |
|---|---|---|---|
| `preview` | is the shoot usable at all? | ~25 k | ~45 s |
| `reduced` | quick web/AR check | ~50 k | ~1 min |
| `medium` | general purpose | ~100 k | ~1.5 min |
| `full` | **default for printing** | ~100 k, best textures | **~100 s** |
| `raw` | maximum geometry, no simplification | very high | slowest |
| `custom` | explicit polygon budget | you decide | ≈ `full` |

Measured on this machine with 61 × 4032×3024 images. Time scales roughly with image count.

Workflow that wastes the least time: run `preview` first, look at the result, then re-run
at `full` only if the shape is right.

**Custom detail** gives a polygon budget, which is what you actually care about for
printing:

```bash
./bin/pg build my-object --polygons 300000 --texture 2k
```

`--polygons` implies `--detail custom`. Texture size is irrelevant for a plain STL print
but matters if you keep the OBJ for a coloured/multi-material workflow.

## Other build options

| Option | Meaning |
|---|---|
| `--order sequential` | photos are a continuous orbit; speeds up matching. Use for turntable/video-frame sets |
| `--order unordered` | default; safest for handheld multi-pass shoots |
| `--sensitivity high` | more aggressive feature detection — try it when a low-texture object fails to align |
| `--no-masking` | disable automatic object isolation; use when masking clips part of the subject |

## Checkpoints

`pg build` always passes `--checkpoint projects/<name>/.checkpoint`. Object Capture reuses
the alignment work stored there, so re-running the same project at a different detail level
is markedly faster. Delete the folder if you change the contents of `images/`.

## What `pg build` produces

```
output/model/
  baked_mesh_<id>.obj        geometry + UVs      ← input to pg stl
  baked_mesh_<id>.mtl        material reference
  baked_mesh_<id>.usda       USD scene           ← preview in Finder / Preview.app
  baked_mesh_<id>_tex0.png   base colour
  baked_mesh_<id>_norm0.png  normal map
  baked_mesh_<id>_ao0.png    ambient occlusion
  baked_mesh_<id>_roughness0.png
  baked_mesh_<id>_disp0.exr  displacement
```

For a single self-contained file instead, call `objcap` directly with a `.usdz` output
path — see [06-reference.md](06-reference.md).

## Next

Scale, watertightness and slicer hand-off: [04-print-prep.md](04-print-prep.md).
