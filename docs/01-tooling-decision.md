# Tooling decision

**Decision (2026-08-02): reconstruct with Apple Object Capture, driven by our own
`objcap` CLI written in this repo. Post-process with `mesh2stl.py` (trimesh).**

## The candidates, verified

### Apple Object Capture — `PhotogrammetrySession` (RealityKit) — CHOSEN

The engine behind the *Easy Photogrammetry* app you have been using. Easy Photogrammetry is
a GUI wrapper; the underlying reconstruction is identical. Driving the API directly removes
the GUI, gives full parameter control and makes the process scriptable.

- **Runs natively on Apple Silicon**, GPU/Neural-Engine accelerated. On this M2/16 GB a
  61-image `preview` run takes ~45 s.
- **Reads HEIC and JPEG directly** — no transcoding step.
- **Writes OBJ + MTL + PNG + USDA** (directory output) or a single USDZ.
- Verified limits on macOS 26.5: **max 1000 input images, max 16384 px** per image.
- Detail levels: `preview`, `reduced`, `medium`, `full`, `raw`, and macOS-only `custom`
  with an explicit polygon budget — directly useful for 3D printing.
- Free, no account, no cloud upload, no per-model cost.

**The trade-off, stated plainly:** the reconstruction engine itself is Apple's closed
system framework. It is not open source. What *is* open and owned by this project is the
whole surrounding toolchain — `tools/objcap` (Swift, ~150 lines), `bin/pg`, and
`tools/scripts/mesh2stl.py`. There is no proprietary application, no vendor lock-in beyond
"you need a Mac", and the outputs are plain OBJ/STL.

If a strictly open-source engine becomes a hard requirement, the migration target is
COLMAP + OpenMVS (below). `bin/pg` is structured so the reconstruction step is swappable.

### AliceVision / Meshroom — REJECTED

- **No official macOS release at all.** The project wiki states this explicitly and notes
  that Apple Silicon adds a further obstacle to producing binaries.
- The full pipeline requires a **CUDA-capable NVIDIA GPU**. Without one, only "Draft
  Meshing" is available — unusable quality.
- Apple dropped NVIDIA support in macOS 10.14; NVIDIA eGPUs do not work either.
- A Metal port (`MTL-AliceVision`) exists but is experimental, not a release.

Verdict: not viable on this machine.

### COLMAP + OpenMVS — VIABLE FALLBACK, NOT CHOSEN

The genuinely open-source path that works on a Mac:

- **COLMAP 4.1.1 is available via Homebrew** (`brew install colmap`, bottled for ARM) and
  runs the sparse Structure-from-Motion stage on CPU.
- COLMAP's own **dense stereo (PatchMatch) requires CUDA** — permanently unavailable on
  Apple Silicon. So COLMAP alone cannot produce a mesh here.
- **OpenMVS** supplies a CPU PatchMatch densifier plus `ReconstructMesh` / `RefineMesh` /
  `TextureMesh`, and exports PLY/OBJ/glTF. Its `MvgMvsPipeline.py` helper can chain a
  COLMAP frontend.
- **OpenMVS is not in Homebrew** — it has to be built from source (CMake + vcpkg), which
  is a meaningful maintenance cost.

Verdict: fully open source and Mac-capable, but CPU-only, substantially slower, more moving
parts, and lower quality than Object Capture on this hardware for handheld object scans.
Keep as the escape hatch.

### Gaussian splatting (OpenSplat, nerfstudio) — OUT OF SCOPE

Excellent for viewing, poor for printing. Splats are not surfaces; extracting a watertight
printable mesh needs an extra, lossy conversion. Revisit only if the goal changes from
printing to visualisation.

## Why not keep using Easy Photogrammetry

Nothing is wrong with it, and it stays useful as a visual sanity check. But it cannot be
scripted, does not version its settings, hides the parameters that matter (polygon budget,
feature sensitivity, sample ordering), and forces manual file shuffling for every project.
`pg` gives reproducible, recorded runs over the same engine.

## Related

- Commands: [03-pipeline.md](03-pipeline.md)
- Verified API facts and limits: [06-reference.md](06-reference.md)

## Sources

- [Creating a photogrammetry command-line app — Apple Developer](https://developer.apple.com/documentation/RealityKit/creating-a-photogrammetry-command-line-app)
- [Meshroom wiki: MacOS](https://github.com/alicevision/Meshroom/wiki/MacOS)
- [COLMAP installation](https://colmap.github.io/install.html)
- [OpenMVS usage wiki](https://github.com/cdcseacave/openMVS/wiki/Usage)
- API surface read directly from
  `/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/System/Library/Frameworks/RealityFoundation.framework/.../arm64e-apple-macos.swiftinterface`
