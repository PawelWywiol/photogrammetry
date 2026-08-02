# Reference

## `bin/pg`

```
pg frames <project> <video>     extract the sharpest frames from a video into images/
pg check  <project>             audit images/: formats, sharpness, shoot duration
pg prep   <project>             build .prepared/ with truthful file extensions
pg build  <project> [objcap…]   reconstruct -> output/model/
pg stl    <project> [mesh2stl…] convert the OBJ to output/<project>.stl
pg view   <project> [meshview…] render shaded views -> output/<project>-views.png
pg all    <project> [objcap…]   check + build + stl
```

`build` implies `prep` and builds `objcap` on first use. Extra arguments pass straight
through to the underlying tool.

## `tools/objcap` — Object Capture CLI

Swift package, no external dependencies, builds with Command Line Tools alone (no Xcode):

```bash
cd tools/objcap && swift build -c release
```

```
objcap <input-images-dir> <output.usdz | output-dir> [options]

--detail <preview|reduced|medium|full|raw|custom>   default: full
--order <unordered|sequential>                      default: unordered
--sensitivity <normal|high>                         default: normal
--no-masking                                        disable automatic object masking
--polygons <n>                                      polygon budget; implies --detail custom
--texture <1k|2k|4k|8k|16k>                         custom-detail texture size, default 4k
--checkpoint <dir>                                  reusable working dir, speeds up re-runs
```

An output path ending in `.usdz` writes one self-contained USDZ. Any other path is treated
as a directory and receives OBJ + MTL + USDA + texture maps.

## `tools/scripts/frames.py`

```
frames.py <video> <output-images-dir> [options]

--count <n>                  frames to keep (default 150, max 1000)
--candidates-per-frame <n>   frames sampled per kept frame (default 4)
--prefix <name>              output filename prefix (default "frame")
```

Samples `count × candidates-per-frame` frames evenly with ffmpeg, then keeps the sharpest
frame from each time slice — motion blur is dropped without leaving gaps in the orbit.
Requires `ffmpeg` and `ffprobe`.

## `tools/scripts/imgcheck.py`

```
imgcheck.py <images-dir> [--blur-ratio 0.4]
```

Reports real formats (by magic bytes, not extension), resolutions, sharpness distribution
and the shoot's total duration. Warns on blurry frames, mixed resolutions, thin image
counts and shoots long enough for a live subject to move.

## `tools/scripts/meshview.py`

```
meshview.py <mesh> <output.png> [--views 0,90,180,270] [--elevation 20] [--size 700]
```

Headless shaded renders — orthographic point-splat with a z-buffer, no OpenGL and no
display. Geometry only; textures are deliberately ignored, since print quality lives in
the mesh.

## `tools/scripts/mesh2stl.py`

Self-contained `uv` script — dependencies are declared inline, `uv run` fetches them.

```
mesh2stl.py <input.obj|ply|glb> <output.stl> [options]

--scale <f>          multiplier on source units (default 1000: metres -> mm)
--target-size <mm>   scale so the longest bbox edge equals this; overrides --scale
--no-repair          skip winding/normal fixes and hole filling
--ascii              write ASCII STL instead of binary
```

Prints face count, bounding box, watertightness and volume before and after.

## PhotogrammetrySession — verified facts

Read from the macOS 26.5 SDK interface at
`/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/System/Library/Frameworks/RealityFoundation.framework/Versions/A/Modules/RealityFoundation.swiftmodule/arm64e-apple-macos.swiftinterface`,
and confirmed at runtime on this M2/16 GB machine.

| Fact | Value |
|---|---|
| Module | `RealityFoundation`, re-exported by `RealityKit` |
| Availability | macOS 12.0+, iOS 17.0+; **unavailable** on visionOS/watchOS/tvOS |
| `PhotogrammetrySession.limits.maximumNumberOfInputImages` | **1000** |
| `PhotogrammetrySession.limits.maximumInputImageDimension` | **16384** px |
| `Request.Detail` | `preview`, `reduced`, `medium`, `full`, `raw`, `custom` |
| `.custom` detail | **macOS only** — marked unavailable on iOS |
| `Configuration.SampleOrdering` | `unordered`, `sequential` |
| `Configuration.FeatureSensitivity` | `normal`, `high` |
| `Configuration.isObjectMaskingEnabled` | `Bool` |
| `Configuration.meshPrimitive` | `triangle`, `quad` |
| `Configuration.init(checkpointDirectory:)` | macOS 14.0+ |
| `Configuration.ignoreBoundingBox` | macOS 15.0+ |
| `CustomDetailSpecification` | `maximumPolygonCount`, `maximumTextureDimension` (1K–16K), `outputTextureMaps`, `textureFormat` (`png` / `jpeg(quality)`) |
| `Request` cases | `modelFile`, `modelEntity`, `bounds`, `pointCloud`, `poses` |
| `Output.ProcessingStage` | `preProcessing`, `imageAlignment`, `pointCloudGeneration`, `meshGeneration`, `textureMapping`, `optimization` (macOS 14.0+) |
| Output units | **metres** |

### Behaviours that are not in the documentation

- Format is chosen by the **filename extension**, not by content — a JPEG named `.HEIC`
  crashes the process. See [05-gotchas.md](05-gotchas.md).
- Directory vs single-file output is chosen by **`URL.hasDirectoryPath`**, which must be
  set explicitly when constructing the URL.
- Benign USD warnings (`Failed to resolve reference @0/baked_mesh_*_tex0.png@`) are printed
  during the optimisation stage. They do not affect the written output.

## Measured performance — 61 × 4032×3024 JPEG, M2, 16 GB

| Detail | Wall clock | Faces |
|---|---|---|
| `preview` | 45 s | 25 000 |
| `full` | ~100 s | 96 492 |
| `raw` | 84 s | 96 286 |
| `custom --polygons 2000000` | 90 s | 95 668 |

The detail level barely moved the face count on this dataset because the **input** was the
limit, not the setting — see [05-gotchas.md](05-gotchas.md). On a well-captured static
object the levels separate as documented. Treat `raw` as "no decimation", not "more
reconstruction".

## Environment

- macOS 26.5.2, Apple M2, 16 GB
- Swift 6.3.3 via Command Line Tools — **Xcode is not required**
- `uv` for the Python side; no virtualenv to manage
- Optional: `brew install --cask blender` for heavy mesh surgery (not needed by the pipeline)
