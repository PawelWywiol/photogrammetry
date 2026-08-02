# Photogrammetry → 3D print

Turn a set of ordinary phone photos of a real object into a **3D-printable STL file**.

Photograph an object from every angle, run one command, get a mesh you can drop into your
slicer. Everything runs **locally on your Mac** — nothing is uploaded anywhere, there is no
account and no subscription.

```
photos of an object  →  make my-object  →  projects/my-object/output/my-object.stl
```

---

## What you need

| Requirement | Why | How to get it |
|---|---|---|
| **A Mac with Apple Silicon** (M1/M2/M3/M4…) | The reconstruction engine is Apple's, and it needs this hardware | — |
| **macOS 15 or newer** | The reconstruction API used here | *Apple menu → System Settings → General → Software Update* |
| **Xcode Command Line Tools** | Compiles the small helper program this project uses | Runs automatically during setup, or type `xcode-select --install` in Terminal |
| **Homebrew** | Installs the two tools below | [brew.sh](https://brew.sh) — copy the one-line command from that page into Terminal |
| **uv** | Runs the Python helper scripts without you managing anything | Installed by `make setup` |
| **ffmpeg** | Only needed if you extract photos from a video | Installed by `make setup` |
| **A camera** | An iPhone is perfect. HEIC and JPEG both work | — |

You do **not** need Xcode itself (the big app), a paid developer account, a graphics card,
or any knowledge of programming.

### Installation

Open the **Terminal** app, then paste these lines one at a time:

```bash
cd ~/code/photogrammetry     # wherever you put this folder
make setup
```

`make setup` installs what is missing and then prints a checklist. You should see something
like:

```
macOS      26.5.2 on arm64
swift      Apple Swift version 6.3.3
uv         uv 0.11.29
ffmpeg     present
objcap     not built yet (built automatically on first run)
```

You can re-run `make doctor` at any time to check the same list.

---

## Your first model

**1. Take the photos.** Walk all the way around the object taking a photo every small step —
aim for **100 or more**, with each photo overlapping the previous one by about 70 %. Do
three laps: crouching low, at eye level, and looking down from above. Even light, no hard
shadows. The object must not move.

**2. Put them in a folder.** Create a folder for the project and drop the photos into an
`images` folder inside it:

```
projects/
  my-object/
    images/
      IMG_0001.HEIC
      IMG_0002.HEIC
      ...
```

You can do this in Finder. Name the project folder whatever you like — that name becomes
the command you type.

**3. Run it.**

```bash
make my-object
```

This checks the photos, reconstructs the object, and writes the STL. On an M2 with ~60
photos it takes about two minutes.

**4. Collect the result.**

```
projects/my-object/output/my-object.stl      ← open this in your slicer
projects/my-object/output/model/             ← the coloured/textured version
```

---

## Commands

Run `make` on its own to see this list at any time.

The pattern is **`make <project> <action>`** — your project name first, then what you want
to do with it. Leave the action out to run the whole thing.

| Command | What it does |
|---|---|
| `make my-object` | The full run: check photos → reconstruct → STL. **This is the one you normally want.** |
| `make my-object preview` | Fast rough version (~45 s). Use it to check the photos are usable before committing to a full run |
| `make my-object check` | Audits the photos and warns about problems. Free, takes seconds |
| `make my-object build` | Reconstruct only, without exporting an STL |
| `make my-object stl` | Re-export the STL only, e.g. at a corrected size |
| `make my-object view` | Renders preview images of the mesh so you can look at it without any 3D software |
| `make my-object video ~/Movies/clip.mov` | Pulls the sharpest frames out of a video into `images/` |
| `make my-object clean` | Deletes generated files, keeps your photos |
| `make list` | Lists your projects |
| `make doctor` | Checks that everything is installed |

### Getting the size right

3D printers work in millimetres, and the reconstruction only *estimates* real-world size —
often wrongly. **Measure one dimension of the real object with a ruler**, then:

```bash
make my-object stl                                  # see the size it guessed
./bin/pg stl my-object --target-size 240            # force the longest edge to 240 mm
```

### Scanning a person, a child or a pet

Still photos do not work for anything alive — the subject moves between shots and the
result comes out as a smooth blob. Record a **15–25 second video** while walking around
them instead, then:

```bash
make my-object video ~/Movies/orbit.mov
make my-object
```

Read [docs/07-moving-subjects.md](docs/07-moving-subjects.md) before trying this — it is the
difference between a likeness and a lump.

---

## Privacy

**This repository is public. Your photos and models are not.**

Everything inside `projects/` is git-ignored and never leaves your machine. That matters:
phone photos embed **GPS coordinates, timestamps and device identifiers** in their EXIF
metadata, and a scan can depict a real person.

If you contribute changes, keep real names and personal details out of documentation and
code examples — use a placeholder like `my-object`.

---

## What's inside

| Path | What it is |
|---|---|
| `Makefile` | The friendly commands above |
| `bin/pg` | The pipeline driver that the Makefile calls |
| `tools/objcap/` | A small Swift program written for this project that drives Apple's reconstruction engine |
| `tools/scripts/` | Python helpers: photo audit, video frame extraction, STL export, mesh preview |
| `docs/` | The knowledge base — start at [docs/INDEX.md](docs/INDEX.md) |
| `projects/` | Your scans. Private, git-ignored |

### What is `bin/pg`?

`pg` is a shell script written for this project — it is the thing that actually does the
work, and the `Makefile` is just a friendlier way to call it. It runs five steps:

1. **check** — audits your photos: real file format, sharpness, how long the shoot took.
2. **prep** — works around a quirk where iPhone photos are sometimes named `.HEIC` while
   actually containing JPEG data, which crashes the reconstruction engine. It builds a
   folder of correctly-named shortcuts and never touches your originals.
3. **build** — runs `tools/objcap`, a ~150-line Swift program written here that drives
   Apple's **Object Capture** (`PhotogrammetrySession`) — the same engine behind Mac apps
   like *Easy Photogrammetry*. Using it directly makes the process scriptable and puts
   every setting under your control.
4. **stl** — converts the result to a print-ready STL: fixes the units, repairs the mesh,
   and stands it on the build plate.
5. **view** — renders preview images of the mesh.

You can call it directly if you want the extra options:

```bash
./bin/pg                       # shows all commands and options
./bin/pg build my-object --detail raw --sensitivity high
```

Why this engine and not Meshroom or COLMAP: see
[docs/01-tooling-decision.md](docs/01-tooling-decision.md). Short version — Meshroom has no
macOS build and needs an NVIDIA card; COLMAP's mesh stage needs the same. Apple's engine is
the only one that is both fast and native here.

---

## When the result is disappointing

Quality is decided when you take the photos, not by any setting — this was measured, not
assumed. Before changing options, run:

```bash
make my-object check
```

and act on what it tells you. The usual causes, in order:

1. **The subject moved.** Anything alive. → shoot video, see above.
2. **Too few photos**, or gaps in coverage. → aim for 100+, three laps at different heights.
3. **The subject is too small in the frame.** → get closer; it should fill 70–80 % of the
   frame height.
4. **Blurry photos.** → `make my-object check` lists them; delete them.
5. **Shiny, transparent or plain untextured surfaces.** → dust with matte/chalk spray.

Full troubleshooting log: [docs/05-gotchas.md](docs/05-gotchas.md).

---

## Documentation

Start at **[docs/INDEX.md](docs/INDEX.md)**. It covers the tooling decision, how to shoot,
the pipeline, print preparation, moving subjects, a log of problems and their fixes, and a
full command reference.
