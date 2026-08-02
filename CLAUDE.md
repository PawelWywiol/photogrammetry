# Photogrammetry → 3D print

## What this repo is for

Turning iPhone photos of real objects into **3D-printable models**. One folder per object
under `projects/`. The deliverable of every project is a print-ready **STL**.

## Goals

- Reproducible, scripted reconstruction — no manual GUI file shuffling.
- Everything about a model recorded in the repo: photos in, settings used, mesh out.
- A knowledge base in `docs/` that grows with every project.

## Stack

| Stage | Tool | Where |
|---|---|---|
| Reconstruction | Apple Object Capture (`PhotogrammetrySession`) via our own Swift CLI | `tools/objcap/` |
| Orchestration | bash driver | `bin/pg` |
| Mesh → STL | `trimesh` via a self-contained `uv` script | `tools/scripts/mesh2stl.py` |

Rationale and the rejected alternatives (Meshroom, COLMAP+OpenMVS): `docs/01-tooling-decision.md`.
The reconstruction engine is Apple's closed framework; everything else here is ours and the
reconstruction step in `bin/pg` is deliberately swappable.

## Commands

`make` is the user-facing surface; `bin/pg` is what it drives. Use `make` in anything
user-facing, `bin/pg` when you need options.

Syntax is `make <project> [action]` — project first, action optional (default: full run).

```bash
make my-object                         # check + reconstruct (full) + STL
make my-object preview                 # ~45 s sanity run
make my-object check                   # audit photos only
make my-object video clip.mov          # moving subject: video -> sharpest frames

./bin/pg build my-object --detail raw --sensitivity high   # full option surface
```

Start with `preview` (~45 s) to confirm the shoot is usable, then re-run at `full`.

## Layout

```
projects/<name>/
  images/     ← hand-managed source photos. NEVER written to by a script.
  NOTES.md    ← what the object is, how it was shot, its MEASURED real-world size
  .prepared/  ┐
  .checkpoint/├ generated, disposable
  output/     ┘
Makefile              user-facing commands
README.md             install + usage, written for non-programmers
tools/objcap/         Swift CLI over PhotogrammetrySession
tools/scripts/        Python post-processing
bin/pg                pipeline driver
docs/                 knowledge base — start at docs/INDEX.md
```

`projects/` is entirely git-ignored except `projects/README.md`.

## Rules

- **Never modify `projects/*/images/`.** Extension fixes go into the generated
  `.prepared/` symlink folder, never in place.
- **Always verify scale against a real measurement.** Object Capture's metric estimate is
  unreliable for plain Camera-app photos. `mesh2stl.py --target-size <mm>` corrects it.
  Record the measurement in the project's `NOTES.md`.
- **Quality problems are capture problems.** Detail level, sensitivity and polygon budget
  were measured to make almost no difference on a badly captured set. When output is poor,
  run `pg check` and look at the photos before touching settings.
- **Anything alive needs video, not stills.** `pg frames`, not a minute-long photo walk.
  See `docs/07-moving-subjects.md`.
- **Do not guess about APIs or tools.** Verify against the SDK interface files, official
  docs, or an actual run. `docs/06-reference.md` records what has been verified.
- After solving anything non-obvious, append a dated entry to `docs/05-gotchas.md` and
  update `docs/INDEX.md`.

## Documentation

`docs/INDEX.md` is the catalog — read the one file you need, do not bulk-load the folder.
It is the self-learning knowledge base for this project.

## Privacy — the repository is public

- `projects/` contents are **git-ignored**. Photos, meshes and notes never leave the machine.
- Photos carry EXIF **GPS coordinates, timestamps and device IDs**. Never commit them, never
  paste them into an issue, never attach a reconstruction that came from private photos.
- Keep real names out of tracked files — project folder names are local-only, but docs,
  `CLAUDE.md` and code examples are public. Use placeholders like `my-object`.

## Current state

- Pipeline verified end to end on a real 61-image project (→ watertight ~96 k-face STL, 98 s).
- On that project quality was capture-limited, not tool-limited — proved across 5
  configurations (`docs/05-gotchas.md`). Fix is a re-shoot as video, not a setting.
