# Printing, plates and slicers

What the slicer needs and how to prove it gets it. Everything here was learned on a Bambu A1 with an AMS lite and
Bambu Studio 2.08; `cadkit` implements it.

## The printer is a parameter

`cadkit.Printer(bed=256, margin=5, layer=0.2, nozzle=0.4)`, default `cadkit.A1`. Put one in the project's params
(`printer` field or property) and pass it to `checks.printable_problems`, `checks.off_layer_z` and `plates.pack`.

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

## Multi-color (AMS)

- **One color change per plate.** Color swaps on an AMS lite take a while and waste filament. Make color regions
  separable by height (lower color up to Z, upper above) and keep two-color parts off single-color plates
  (`plates.pack` does both: it pools two-color parts onto their own plates).
- **Model:** a two-color part is a `Compound` of two bodies, lower color first, each with `.color` and a `.label`
  that says its role (`ladder_wood`, `ladder_steel`). The label picks the filament.
- **The upper color rests on the lower one:** `checks.unsupported(upper, lower) == 0`. Build it in, too: clip the
  upper body to the lower body's 2D footprint (`upper &= extrude(footprint, big)`).
- **CAD:** `paint.painted(lower, color, upper, color)` fuses them into one solid with face colors; `paint.export_step`
  writes the face colors so Onshape shows one part, two colors.
- **Filaments:** keep the AMS slot per color in params (`filament_gray = 1`, `filament_brown = 2`). Ask the user
  which slot holds what; their screenshot of a hand-colored project tells you.

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

## Check it the way the slicer reads it

Unit tests can't tell you what the slicer does with a file. Bambu Studio has a CLI; `cadkit.bambu` drives it:

```python
from cadkit import bambu, bambu3mf
back = bambu.roundtrip("out/plates/p1.3mf")            # Bambu loads it and saves it back
assert bambu3mf.read_filaments(back) == ...            # same filament per part
assert bambu3mf.object_sizes(back) == bambu3mf.object_sizes("out/plates/p1.3mf")   # same mesh per object
r = bambu.slice_report("out/plates/p1.3mf")            # {"grams": {1: 0.6, 2: 12.1}, "layers": [((2,), 0, 11), ((1,), 12, 18)]}
```

- `slice_info.config` numbers filaments from 0 in `layer_filament_list`; `slice_report` converts to 1-based.
- The CLI writes `result.json` into its working directory; `cadkit.bambu` runs it in a temp dir.
- Bambu saves 32-bit floats, so sizes agree to 0.1 mm, not exactly.
- Make the slicer test `@pytest.mark.slow` and `skipif(bambu.find() is None)`, so the suite runs without it.

## Before the first real print

Print a fit-test coupon (`examples/fit-coupon`): three variants of each joint, marked 1/2/3. Pick the one that
fits and put its clearance in params. Clearances depend on the printer, the filament and the slicer profile.
