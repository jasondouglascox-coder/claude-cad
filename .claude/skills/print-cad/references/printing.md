# Printing, plates and slicers

What the slicer needs and how to prove it gets it. Everything here was learned on a Bambu A1 with an AMS lite and
Bambu Studio 2.08; `cadkit` implements it, and the user's own setup comes from `cadkit.settings`.

## The user's setup comes from settings

Printer, colors, slicer and projects folder are the user's, not the code's: `CADKIT_*` environment variables or
an untracked `cadkit.toml` (`cadkit.toml.example` lists every key). Check what's in effect before designing:

```bash
cd cadkit && uv run python -m cadkit.settings     # every value and where it came from
```

Nothing set = a Bambu A1 (256 × 256 mm, 0.4 nozzle, 0.2 layers), 4 AMS colors, Bambu Studio, projects in
`examples/`. Never edit cadkit to fit a printer; if a value is missing from settings, add the setting.

## The printer is a parameter

`cadkit.Printer()` takes its defaults from settings (bed, bed_y for rectangular beds, margin, layer, nozzle);
`cadkit.A1` is the literal A1. Put one in the project's params (`printer: Printer = field(default_factory=Printer)`)
and pass it to `checks.printable_problems`, `checks.off_layer_z` and `plates.pack` (they default to it anyway).
Size long parts against `printer.usable_x`/`usable_y`; a part bigger than the user's bed should fail its test with
the footprint and the bed, and you split it.

## Print flat, no supports

- Parts are 2D profiles extruded to a thickness, made in print orientation (`make()`), placed into the assembly by
  a separate `place()` transform.
- `checks.downward_faces(part)` lists every face that faces down above the bed. Each one is a bridge (fine if
  short and anchored at both ends) or needs support (not fine). Review them; don't assume.
- Things that get missed:
  - **A feature over another feature's hole.** Tie plates printed on top of the ties sat right over the slots the
    truss tabs come up through, so each bridged a 3.4 mm hole on 0.3 mm anchors. The fix was the user's: leave the
    slot open to the sky (no plate on that tie).
  - **A tie cut by a joint socket.** The first tie after a jigsaw socket lost 0.5 mm under its plate. Clipping the
    upper color to the lower color's footprint fixed every case at once.
- Walls at least two nozzle widths; nothing under one nozzle width survives slicing.

## Layers

Every top, color seam and inlay sits on a multiple of the layer height: `checks.off_layer_z(part, printer) == []`.
A seam at 2.3 mm with 0.2 mm layers makes the slicer split a layer, and the color change lands mid-layer.
The layer height is the user's (settings), so make heights follow it: in params `__post_init__`, pass absolute
heights through `printer.snap(z)` (nearest boundary, first layer included) and thicknesses stacked on another
height through `printer.layers(t)` (whole layers). On 0.2 mm layers both leave round values alone; on 0.16 or
0.12 they keep every top on a boundary (`examples/fit-coupon/fitcoupon/params.py`).

## Multi-color (AMS)

- **Color changes are a budget, not a law.** Each swap costs time and purged filament. The budget per plate is
  `settings().color_changes` (default 1) and the printer's colors are `settings().colors` (default 4; 1 = no AMS).
  - Default to the cheapest layout: color regions separable by height (lower color up to Z, upper above: one swap
    per seam), multi-color parts off single-color plates (`plates.pack` does that).
  - `plates.color_changes(items)` counts a plate's swaps layer by layer; colors side by side in the same layers
    swap every layer. `checks.color_problems(items)` says what's over the user's limits, with the options.
  - **When a design wants more swaps or colors than the setup allows, tell the user before building it:** the
    count, roughly what it costs, and the alternatives (split by height, print the detail separately and glue it,
    drop a color, relief instead of color). If they accept, record it in the spec and pass `Plate(...,
    color_changes=n)` for that plate so the build stops warning. `write_plates` warns on any other plate over budget.
  - **One-color printers:** with `colors = 1`, `write_plates` puts every body on filament 1 and packing mixes
    everything; design so the part still reads in one color (raised marks, texture), and say so.
  - A plate needing a filament past `colors` stops with the options; tests check filaments through
    `settings().filament(n)` so they pass on any setup.
- **Model:** a two-color part is a `Compound` of two bodies, lower color first, each with `.color` and a `.label`
  that says its role (`ladder_wood`, `ladder_steel`). The label picks the filament.
- **The upper color rests on the lower one:** `checks.unsupported(upper, lower) == 0`. Build it in, too: clip the
  upper body to the lower body's 2D footprint (`upper &= extrude(footprint, big)`).
- **CAD:** `paint.painted(lower, color, upper, color)` fuses them into one solid with face colors; `paint.export_step`
  writes the face colors so Onshape shows one part, two colors.
- **Filaments:** keep the AMS slot per color in params (`filament_gray = 1`, `filament_brown = 2`). Ask the user
  which slot holds what; their screenshot of a hand-colored project tells you.

## Slicers

`cadkit.slicers.active()` is the user's slicer (`settings().slicer`): `bambu` (built in) or `none` (plates only,
slicer checks skipped). Others plug in through `cadkit/slicers/` (see CONTRIBUTING.md). Projects and tests use the
interface, never a slicer module directly:

```python
from cadkit import slicers
s = slicers.active()
s.read_filaments(path); s.roundtrip(path); s.same_objects(a, b); s.slice_report(path)
```

Mark live slicer tests `@pytest.mark.slow` and `skipif(not slicers.active().available())`.

## Bambu Studio 3MF: plates that open colored

A plain 3MF (e.g. build123d's `Mesher`) opens with *"The 3mf is not from Bambu Lab, load geometry data and color
data only"* and every part on filament 1. Bambu Studio reads a filament per part only from its own project format,
so `cadkit.bambu3mf.write` writes that:

- `3D/3dmodel.model`: `<metadata name="Application">BambuStudio-…</metadata>`, one object per printed part, its
  color bodies as components pointing into `3D/Objects/object_N.model`, one build item per object (so a two-color
  part is one object and the upper color can't drop onto the bed).
- `Metadata/model_settings.config`: per object a name and default `extruder`; per part (`<part id=…>`, id = the mesh
  id) a name and `extruder`. Bambu leaves the part's extruder out when an object has one part.
- `Metadata/project_settings.config`: copied from a template Bambu Studio saved (`bambu_a1_project_settings.config`,
  A1 0.4, 0.20mm Standard, PETG/PETG/PLA/PLA). **Without it Bambu Studio's CLI crashes** on the file. To target
  another printer, save any project from Bambu Studio, unzip it, and pass that file as `settings=`.
- **Ids are one sequence across the whole package** (meshes 1, 2 → object 3; meshes 4, 5 → object 6), as Bambu
  writes them. Bambu keys meshes by id alone, whatever file they're in: numbering each object file from 1 made the
  three different ladders of a plate open as three copies of the first one.
- Meshes come from `shape.tessellate()` with coincident vertices merged (OCC tessellates face by face), degenerate
  triangles dropped, and outward winding. Test: every edge shared by two triangles, signed volume = solid volume.

Placement: items are packed inside the bed from the margin; if Bambu's own arrangement is wanted, Arrange (A) is
fine. Open the files with File → Open Project (or "open as project" when asked).

- **Prime tower.** Every plate that changes color gets a prime tower, and Bambu refuses to slice a plate with a
  part where it prints ("gcode path conflicts found between WipeTower and …").
  - `cadkit.plates.pack` keeps that corner free on multi-color plates: `slicers.active().tower_keepout()`, read from
    `wipe_tower_x/y` and `prime_tower_width`; on the A1 template it's x 31-78, y 210-257.
  - A plate that needs the corner (a round 10" flower) moves the tower with `bambu3mf.write_settings(tower=...)`.
- **Every plate in one project:** `write_plates(..., combined="kit")` also writes `kit.3mf`, a tab per plate.
  - Plates printed more than once are named "(print n)".
  - Bambu lays plates out every 1.2 beds, left to right then down, about √n columns. The tower spot is a list
    with one entry per plate, and cadkit repeats the kept corner for each.
  - One file shares one set of project settings. Plates that need different settings (0.08 vs 0.2 mm layers,
    another tower corner) go in separate files.
  - A one-plate file is byte-for-byte the plain project.

## Sharing on MakerWorld

One model per project, one **print profile** per variant (a profile is one project 3MF holding all its plates):
the railroad's starter bay in each style, its corners, the wire-rail test; the sunflower's 16" and 10". A visitor
picks a profile and gets every plate it needs.

1. **Build the profiles sliced:** a `build makerworld` command writes `out/makerworld/<profile>.3mf` through
   `slicers.active().slice_all` (Bambu: `--slice 0`). Every plate then carries its G-code and the
   `Metadata/plate_N.png` thumbnail MakerWorld shows. A slow test checks each plate has both.
2. **Name the plates** for the visitor ("front_quarter (print 4)"). Say in the description which plates are
   alternatives and what each needs: filaments per AMS slot, layer height when it isn't 0.2 mm, glue or hardware.
3. **Photos:** the README renders (`docs/images/`) for the cover, plus a photo of the real print once there is one.
   MakerWorld favors real photos.
4. **Check before uploading:** open each profile in Bambu Studio. The colors should be right, there should be no
   conflict warnings, and the plate count and order should match the description.
5. **The user uploads.** Publishing is theirs: prepare the files, renders and description text, and never post or
   upload on their behalf. They also pick the license.

## Check it the way the slicer reads it

Unit tests can't tell you what the slicer does with a file. Bambu Studio has a CLI; `cadkit.bambu` drives it
(`cadkit.slicers` wraps it as the `bambu` slicer; projects use the wrapper):

```python
from cadkit import bambu, bambu3mf
back = bambu.roundtrip("out/plates/p1.3mf")            # Bambu loads it and saves it back
assert bambu3mf.read_filaments(back) == ...            # same filament per part
assert bambu3mf.same_objects(back, "out/plates/p1.3mf")   # same mesh per object, within 0.01 mm
r = bambu.slice_report("out/plates/p1.3mf")            # {"grams": {1: 0.6, 2: 12.1}, "layers": [((2,), 0, 11), ((1,), 12, 18)]}
```

- `slice_info.config` numbers filaments from 0 in `layer_filament_list`; `slice_report` converts to 1-based.
- The CLI writes `result.json` into its working directory; `cadkit.bambu` runs it in a temp dir.
- Bambu saves 32-bit floats, so compare sizes within a tolerance (`same_objects`), never by rounding: 60.15 comes
  back as 60.149…, which rounds to 60.1 instead of 60.2 and reports a false mismatch.
- Make the slicer test `@pytest.mark.slow` and `skipif(not slicers.active().available())`, so the suite runs
  without one.

## Before the first real print

Print a fit-test coupon (`examples/fit-coupon`): three variants of each joint, marked 1/2/3. Pick the one that
fits and put its clearance in params. Clearances depend on the printer, the filament and the slicer profile.
