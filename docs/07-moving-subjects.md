# People, children and pets — subjects that will not hold still

Photogrammetry solves for **one rigid shape seen from many angles**. If the subject changes
between photos, the solver cannot tell "the arm moved" from "the arm is shaped differently",
and it averages the poses into a smooth blob. You get the right silhouette and no detail.

This is the single biggest cause of disappointing scans of people. No reconstruction setting
fixes it — see the measured proof in [05-gotchas.md](05-gotchas.md).

## Shoot video, not stills

A child holds still for about ten seconds. A 61-photo walk-around takes a minute, and in
that minute they turn their head, drop their arms, shift weight and change expression.

**Do this instead:**

```bash
# 1. record a 15–25 s orbit video on the iPhone
# 2. extract the sharpest frames straight into a new project
./bin/pg frames my-object ~/Movies/orbit.mov --count 150

./bin/pg check my-object
./bin/pg all   my-object --detail full
```

`pg frames` samples several candidates per output frame and keeps the sharpest of each
time slice, so motion-blurred frames are dropped without leaving gaps in the orbit.

## Recording the video

| | Setting |
|---|---|
| Mode | Video, **4K at 60 fps** (60 fps means less motion blur per frame) |
| Distance | **1–1.5 m** — the subject should fill **70–80 % of the frame height** |
| Movement | Walk a full circle in **15–25 s**, smooth and continuous |
| Passes | 2–3 circles at different heights (knee, chest, above head), all inside ~60 s |
| Focus | Tap and hold to lock AE/AF on the subject before starting |
| Stabilisation | Keep it on; move your feet, not the phone |
| Light | Overcast or shade. Never direct sun |

For a small child, one adult orbits with the phone while another keeps the child's
attention fixed on one spot. A "statue game" for 20 seconds is realistic; a minute is not.

## What matters most, in order

1. **Time.** Every second of shoot is a chance for the subject to move. Shorter beats
   better-composed.
2. **Frame filling.** Detail is bounded by pixels landing on the subject. A subject that
   is a third of the frame throws away most of your camera's resolution.
3. **Consistent distance.** Do not mix wide full-body shots with tight close-ups in the
   same set — the solver weights them inconsistently. Pick one framing and keep it.
4. **Sharpness.** `pg check` reports the blurry ones. Delete them; they add noise, not
   detail.

## Things that will not reconstruct

- **Hair.** Fine strands have no stable features. Expect a smooth helmet. This is normal
  and every photogrammetry system does it.
- **Hands and fingers.** Thin, self-occluding and always moving. Ask for a pose with hands
  flat against the body or in pockets.
- **The soles of the feet.** Never visible. Fine for printing — you want a flat base.
- **Plain single-colour clothing.** Patterned clothes reconstruct noticeably better than a
  plain block of colour.

## Realistic expectations

Even a perfect handheld phone capture of a person gives you a **likeness**, not a portrait
bust: recognisable proportions, face and clothing folds, and smooth skin. Studio results
you may have seen use dozens of cameras firing simultaneously, which removes the time
problem entirely.

For printing, this is usually fine — at 10–20 cm tall, printed at 0.1–0.2 mm layers, the
detail that survives is roughly the detail a good handheld capture provides.

## Checklist before you build

```bash
./bin/pg check <project>
```

Act on these warnings:

- `shoot took Ns` over ~120 s → the subject moved; re-shoot as video.
- `N blurry images` → delete them.
- `N images is thin` → aim for 100–150.
- `mixed resolutions` → you cropped or edited some photos; use originals only.
