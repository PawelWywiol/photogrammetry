# Documentation index

Knowledge base for turning iPhone photos into 3D-printable models. Read the file you
need — do not bulk-load this folder.

New here? Start with the [README](../README.md) — installation and first model.

| File | What's inside |
|---|---|
| [01-tooling-decision.md](01-tooling-decision.md) | Which photogrammetry engine we use and why; verified comparison of Object Capture / Meshroom / COLMAP+OpenMVS; the open-source trade-off |
| [02-capture-guide.md](02-capture-guide.md) | How to shoot photos with an iPhone so the reconstruction succeeds: coverage, lighting, turntable vs orbit, camera settings, image counts |
| [03-pipeline.md](03-pipeline.md) | Step-by-step commands: `pg check` → `pg build` → `pg stl`. Detail levels, timings, checkpoints, output layout |
| [04-print-prep.md](04-print-prep.md) | Real-world scale, units, watertight meshes, decimation, orientation, slicer hand-off |
| [05-gotchas.md](05-gotchas.md) | Dated log of problems hit and how they were solved. Check here first when something breaks |
| [06-reference.md](06-reference.md) | CLI reference for `pg`, `objcap`, `mesh2stl.py`, `frames.py`, `imgcheck.py`, `meshview.py`, plus verified PhotogrammetrySession API facts and limits |
| [07-moving-subjects.md](07-moving-subjects.md) | **Scanning people, children and pets.** Why still photos fail on live subjects and how to shoot video instead. Read this before scanning anything that breathes |
| [08-mesh-optimisation.md](08-mesh-optimisation.md) | `pg opt` — welding vertices, denoising, remeshing, decimation, sharpening. Presets, measured fidelity, and what post-processing can and cannot fix |
| [09-choosing-photos.md](09-choosing-photos.md) | `pg triage` — using the solver's camera poses to find which photos are unplaceable, redundant or load-bearing. Why deleting blurry frames usually backfires |

## Conventions

- One folder per model under `projects/<name>/`.
- `projects/<name>/images/` is the **only** hand-managed folder. Never edit it from a script.
- Everything else under `projects/<name>/` is derived and safe to delete: `.prepared/`,
  `.checkpoint/`, `output/`.
- Add a `projects/<name>/NOTES.md` with what the object is, how it was shot, and its
  measured real-world size.

## Adding to this knowledge base

After solving a non-obvious problem, append a dated entry to `05-gotchas.md`
(problem → cause → fix). Update this index when you add a file.
