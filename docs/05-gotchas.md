# Gotchas — problems hit and how they were solved

Newest first. Append a dated entry whenever you solve something non-obvious.

---

## 2026-08-02 — Blobby, detail-free mesh: it is the capture, not the settings

**Symptom:** a project reconstructed into a recognisable but mushy figure — correct
silhouette, no surface detail. Suspicion fell on the detail level.

**What was measured.** The same 61 images, five configurations:

| Configuration | Faces |
|---|---|
| `--detail full` | 96 492 |
| `--detail raw` (shared checkpoint) | 95 620 |
| `--detail custom --polygons 2000000` | 95 668 |
| `--detail raw` (fresh checkpoint) | 96 286 |
| `--detail raw --order sequential --sensitivity high` | 96 028 |

Every configuration lands on ~96 k triangles. A 2-million-polygon budget changes nothing,
so **nothing is being decimated away — the solver has no more detail to give**.

Confirmed from the other direction: the displacement map was **entirely zero**, and the
normal map carried almost no high-frequency signal (mean |high-freq| 0.37/255 versus
2.54/255 for the colour map). There is no detail hidden in the texture maps either.

**Cause, found by looking at the input photos:** the subject was a **living person**, shot
over **62 seconds**. Across the sequence the pose changes repeatedly — arms in different
positions, head turned different ways — and the framing swings from whole-subject-small to
close-up-large. Photogrammetry solves for one *rigid* shape; a subject that changes between
frames gets averaged into a smooth blob. Separately, when the subject occupies a third of
the frame, most of the sensor resolution is spent on the background.

**Fix:** capture, not configuration. Shoot a 15–25 s orbit **video** and extract frames —
`pg frames <project> <video>`. See [07-moving-subjects.md](07-moving-subjects.md).

**Also added:** `pg check` now measures per-image sharpness and the shoot's total duration,
and warns when a shoot ran long enough for a live subject to move. Those two numbers would
have identified this in seconds.

**Lesson:** when output quality is flat across every quality setting, stop turning knobs
and go look at the input.

---

## 2026-08-02 — iPhone `.HEIC` files that are actually JPEG crash Object Capture

**Symptom:** `objcap` died with an uncaught Objective-C exception during processing:

```
*** Terminating app due to uncaught exception 'NSInternalInconsistencyException',
    reason: 'HEIF file is expected.'
    ... CoreOCModules OCNonModularSPI_CMPhoto_readVersion ...
```

**Cause:** every file in the project's `images/` was named `*.HEIC` but `file --mime-type`
reported `image/jpeg`. Some AirDrop/export/sync paths convert HEIC to JPEG while keeping
the original filename. **Object Capture dispatches on the filename
extension, not on the file's magic bytes**, so it opened a JPEG with its HEIF reader and
threw.

**Fix:** `pg build` now runs `pg prep` first, which builds `projects/<name>/.prepared/` — a
folder of symlinks whose extensions match the real container type reported by
`file --mime-type`. The originals in `images/` are never touched.

`pg check <project>` reports the mismatch count so you see it before it bites.

---

## 2026-08-02 — Directory output rejected with `PhotogrammetrySession.Error error 1`

**Symptom:** requesting an OBJ folder instead of a `.usdz` file failed instantly:

```
error: cannot start processing: The operation couldn't be completed.
       (RealityFoundation.PhotogrammetrySession.Error error 1.)
```

Error case 1 is `invalidOutput`. The target directory existed and was writable.

**Cause:** RealityKit decides "single USDZ file" vs "OBJ + USDA folder" from
`URL.hasDirectoryPath`. `URL(fileURLWithPath:)` does **not** infer that from the
filesystem — the flag has to be set explicitly.

**Fix:** in `tools/objcap/Sources/objcap/main.swift`, build the output URL with
`URL(fileURLWithPath: path, isDirectory: <not a .usdz>)`.

---

## 2026-08-02 — "Mesh is not watertight" on a mesh that is actually closed

**Symptom:** `mesh2stl.py` warned that the OBJ was not watertight, yet re-loading the
exported STL showed Euler number 2, one connected component and zero boundary edges — a
textbook closed manifold.

**Cause:** OBJ stores per-face texture coordinates, so vertices along UV seams are
duplicated. Topologically the surface looks torn even though it is geometrically sealed.
STL has no UVs, so the duplicates merge on re-import and the "problem" disappears.

**Fix:** `mesh2stl.py` calls `mesh.merge_vertices(merge_tex=True, merge_norm=True)` before
reporting or repairing. Apply the same merge in any other tool before trusting a
watertight check on an OBJ.

---

## 2026-08-02 — Meshroom is not an option on this machine

Not a bug, a dead end worth recording so nobody re-investigates: AliceVision/Meshroom has
**no official macOS build** and its full pipeline **requires CUDA**, which Apple Silicon
cannot provide. See [01-tooling-decision.md](01-tooling-decision.md).

Likewise COLMAP installs cleanly from Homebrew but its **dense stereo stage requires
CUDA**, so COLMAP alone cannot produce a mesh here — it needs OpenMVS for densification,
and OpenMVS is not in Homebrew and must be built from source.

---

## 2026-08-02 — Headless mesh rendering on macOS

`qlmanage -t` on an STL hangs indefinitely from a non-interactive shell. `trimesh`'s
`scene.save_image()` needs `pyglet<2` and still crashes on macOS with
`CocoaAlternateEventLoop object has no attribute platform_event_loop`.

**What works** for a quick shape sanity check: `matplotlib` with the `Agg` backend and
`Poly3DCollection`, on a mesh decimated with `fast-simplification`. Slow and unlit, but it
answers "is this a real object or garbage?" without a display.

For a proper look, open `output/model/*.usda` or a `.usdz` in Preview.app.
