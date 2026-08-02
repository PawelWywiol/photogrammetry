# Capture guide — shooting photos for photogrammetry

Reconstruction quality is decided at capture time. No setting in `pg` recovers a bad shoot —
this was measured, not assumed ([05-gotchas.md](05-gotchas.md)).

> **Scanning a person, child or pet?** Still photos are the wrong tool. Read
> [07-moving-subjects.md](07-moving-subjects.md) first.

## The rules that matter most

1. **Overlap.** Aim for **≥70 % overlap between consecutive photos, never below 50 %**.
   In practice: move a small step between shots, not a big one.
2. **Full coverage.** Orbit the object completely at **three heights** — low (looking
   slightly up), eye level, high (looking down). Three full 360° passes.
3. **Count.** Apple recommends **20–200 images** for an object, with **100+** as the
   target for a good result. Hard ceiling is 1000. Around 60 works but leaves gaps.
4. **Keep the object still — and rigid.** Move yourself around the object, or rotate the
   object on a turntable, never both in one pass. A subject that changes shape or pose
   between frames is averaged into a smooth blob.
5. **Fill the frame.** Detail is bounded by how many pixels land on the subject. Aim for
   the subject occupying **70–80 % of the frame height**, and keep the distance constant —
   do not mix wide shots with close-ups in one set.
6. **Sharpness beats resolution.** Motion blur and out-of-focus frames poison the
   alignment. Steady hands, good light, tap-to-focus on the object.
7. **Finish fast.** Every extra minute is another chance for the subject, the light or the
   scene to change.

## Lighting

- **Diffuse and even.** Overcast daylight, shade, or a light tent. Avoid hard shadows.
- **Do not move the lights** during the shoot.
- Avoid direct sun and strong specular highlights — a highlight that moves across the
  surface between frames looks like a moving feature and corrupts the solve.

## Surfaces that fail

Photogrammetry needs visible texture. These do not reconstruct:

| Problem surface | Fix |
|---|---|
| Shiny / chrome / glossy | Matte spray (dry shampoo, chalk spray, AESUB scanning spray) |
| Transparent / glass | Same — make it opaque |
| Plain flat colour, no grain | Add temporary texture: dots of removable marker, patterned tape |
| Thin features (hair, wire, leaves) | Accept loss, or model them separately |
| Deep concavities | Extra photos aimed into the cavity |

## Background

- Object Capture's **object masking is enabled by default** in `objcap` and usually
  isolates the subject well.
- Still helps: a **textured, static background** (a rug, a wooden table) for a handheld
  orbit, because the background gives the solver extra alignment features.
- On a turntable it is the opposite — you want a **plain, featureless background**, since
  a static background contradicts the rotating object. Use `--no-masking` only if masking
  visibly eats part of the subject.

## iPhone settings

- Shoot in the **Camera app, photo mode**, highest resolution. HEIC or JPEG both work.
- **Turn off** Live Photos and any auto-enhancement that varies between frames.
- Keep **exposure and focus consistent** — tap and hold to lock AE/AF on the object.
- Do not crop or edit the photos afterwards; EXIF focal length is used by the solver.

## Turntable vs handheld orbit

| | Handheld orbit | Turntable |
|---|---|---|
| Setup | none | turntable + fixed camera + plain backdrop |
| Best for | large / immovable objects | small objects, repeatable results |
| `--order` | `unordered` | `sequential` |
| Gotcha | forget a height band → holes | textured backdrop breaks the solve |

For a turntable, do multiple passes at different camera heights, and flip the object to
capture the underside in a separate pass.

## Capturing the bottom

The face resting on the table is never seen. Two options:

- **Second pass, flipped.** Shoot a full set with the object on its side or upside down,
  put all images in one `images/` folder, and let the solver merge them. Works when the
  object has enough distinctive texture for the two passes to align.
- **Accept it and close the mesh in a slicer.** For a print with a flat base this is often
  what you want anyway.

## Before you build

Run `pg check <project>` — it reports image count, format mismatches and resolution
consistency, and warns if you are below 20 images.

## Sources

- [Capturing photographs for RealityKit Object Capture — Apple Developer](https://developer.apple.com/documentation/realitykit/capturing-photographs-for-realitykit-object-capture)
- [Create 3D models with Object Capture — WWDC21](https://developer.apple.com/videos/play/wwdc2021/10076/)
