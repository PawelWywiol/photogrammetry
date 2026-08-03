# Which photos to keep, and which to drop

```bash
make my-object triage          # ~40 s, no meshing — report only
make my-object triage drop     # same, then park the condemned photos as *.bak
./bin/pg triage my-object --max-gap 12 --write-subset /tmp/keepers
```

`pg triage` answers "which photos are hurting the model" using the solver's own camera
poses rather than guessing from image statistics.

## Why sharpness alone is the wrong question

The obvious idea — delete the blurry photos — was tested here and **made the model twice as
bad** (96 286 → 47 362 faces, [05-gotchas.md](05-gotchas.md)). Two reasons:

1. The soft frames were **consecutive**, so removing them tore a ~65° hole in the orbit.
2. They were soft *because they were shot from close up*, where hand shake shows more — and
   close frames carry the **most pixels on the subject**, i.e. the most detail.

A photo is only worth deleting when it is both **weak** and **redundant**. Redundancy is a
question about orbit geometry, and geometry needs camera poses.

## How the poses are obtained

`PhotogrammetrySession` has a `poses` request that solves camera alignment and stops —
no meshing, no texturing. `objcap` runs it whenever the output path ends in `.json`:

```bash
objcap <prepared-dir> poses.json
```

On 61 × 12 MP photos this takes **~42 s**, versus ~100 s for a full reconstruction. The JSON
holds each placed photo's camera translation and rotation.

## The four signals

### 1. Did the solver place it at all

Photos missing from the poses output could not be positioned. They contribute nothing — the
reconstruction already ignores them. They are the only frames that are unconditionally safe
to delete, and their presence points at a moment in the shoot that went wrong.

### 2. Orbit position, and the gap deleting it would open

Camera positions are projected onto the horizontal plane and converted to an azimuth around
the subject. For each photo, `triage` computes the gap that would be left if it went — its
own gap plus its predecessor's. If that exceeds `--max-gap` (default 15°), the photo is
**load-bearing** and stays, however soft it is.

This is the check that would have prevented the mistake above.

### 3. Distance to the subject

The radius of each camera from the orbit centre. Wildly varying distance is itself a capture
problem, and a shoot done at two distances shows up as two rings.

**Close-range frames are never dropped for softness**, because that is exactly the
combination that cost detail here.

### 4. Sharpness

Variance of the Laplacian, same metric as `pg check`. It only ever acts as a tie-breaker on
frames that are already redundant.

## Reading the output

```
registered:  58 of 61 photos
NOT PLACED:  3 -> ['IMG_1429', 'IMG_1430', 'IMG_1431']
orbit:       median step 5.2deg, largest gap 17.7deg, effective coverage ~357deg
distance:    median 1.05, range 0.35-1.40 (solver units)
height:      spread 0.20
NOTE:        14 photos were taken much closer than the rest (0.47 vs 1.11).
```

| Line | What to do about it |
|---|---|
| `NOT PLACED` | Delete them. Look at what happened in the shoot at that point |
| `largest gap` over ~20° | A hole in the orbit. More photos there, not fewer |
| `effective coverage` well under 360° | You did not get all the way round |
| `distance range` spanning more than ~2× | Inconsistent framing — pick one distance and hold it |
| `height spread` near 0 | Only one height band. Shoot low/mid/high passes |
| `NOTE` about closer photos | Those are your best data. Do not prune them |

The per-photo table then lists only flagged frames, with `DROP` or `keep` and the reason.

## Acting on it — `--drop`

`triage` reports by default and changes nothing. Add `--drop` (or `make <project> triage
drop`) to act on the report:

- every `NOT PLACED` and every `DROP` photo is **renamed** to `<name>.<ext>.bak` in place;
- `check`, `prep`, `build` and `triage` all skip `*.bak`, so the photo stays out of the
  reconstruction without leaving your machine;
- `output/poses.json` and `.checkpoint/` are removed, because both describe a photo set that
  no longer exists — the next build re-solves from scratch;
- nothing is ever deleted. Undo the whole thing with:

```bash
for f in projects/my-object/images/*.bak; do mv "$f" "${f%.bak}"; done
```

Run it without `--drop` first and read the table. `--drop` acts on exactly the frames the
report just condemned, and on nothing else.

**Run it once.** "Soft" means *below half the median sharpness of the surviving photos*, so
every pass grows a fresh tail of new offenders out of frames that were perfectly acceptable
before. One pass removes the genuinely weak frames; repeating it just eats the shoot.

### Removals are judged in sequence, not one at a time

Each candidate is measured against the orbit **as the previously accepted removals left it**,
softest frame first. This matters more than it sounds:

| | Largest gap | Coverage |
|---|---|---|
| 150 photos, before | 7.4° | ~360° |
| 13 dropped, each judged independently | **27.8°** | ~347° |
| 11 dropped, judged in sequence | 13.3° | ~360° |

Frames 0081–0094 were a consecutive run of soft frames. Judged individually every one of
them "leaves only a 6° gap" — and removing the lot tore a 27.8° hole anyway. The sequential
pass keeps 0084 and 0089 as anchors inside the run and stays inside the 15° budget. Measured
on a real 150-frame shoot.

## What it found on a real 61-photo shoot

- **3 photos the solver could not place at all** (`IMG_1429`–`1431`) — invisible to any blur
  metric, since they were perfectly sharp.
- **Two separate orbits**: 14 photos at radius 0.47 and the rest at 1.11 — the photographer
  walked in for a close lap, then back out. This is why the "blurry" frames were clustered.
- **Nothing else safe to drop.** Every soft frame was holding a section of the orbit
  together.

Verified by rebuilding from the 58 keepers:

| Input | Faces |
|---|---|
| all 61 photos | 96 492 – 97 152 (run-to-run variance ~1 %) |
| 58 keepers, 3 unplaceable removed | **97 968** |
| 50 photos, "blurry" ones removed by hand | 47 362 |

Removing the unplaceable photos gives an equivalent model — as expected, since the solver
was already ignoring them. The value is diagnostic, not a quality gain: it tells you those
three photos were wasted, and where in the shoot things went wrong.

The last row is the warning. When triage says "nothing to drop", believe it — the fix is a
better capture, not a cleverer subset.

## The honest limit

Triage finds photos that are **geometrically** unhelpful. It cannot detect that the subject
changed pose between frames — the camera poses look perfectly reasonable in that case,
because the *camera* really was where the solver says it was. Detecting and correcting a
subject that moved is non-rigid structure-from-motion: an active research topic with
published papers but no production-ready open-source implementation.

For live subjects the answer remains capture-side: [07-moving-subjects.md](07-moving-subjects.md).
