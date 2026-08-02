# projects/

One folder per object you scan. **Everything in here is private and git-ignored** — photos,
meshes, notes. Only this file is tracked.

Create a project by making a folder with an `images/` subfolder:

```
projects/
  my-object/
    images/      ← your photos go here
```

Then run `make my-object` from the repository root (or `make my-object check` first).

Do not commit anything from this folder. Photos carry EXIF GPS coordinates, timestamps and
device identifiers, and reconstructions can depict people.
