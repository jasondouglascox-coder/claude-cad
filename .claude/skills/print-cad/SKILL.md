---
name: print-cad
description: Parametric, test-driven CAD for 3D-printed parts in Python (build123d + cadkit), exported as STEP for Onshape/other CAD and as Bambu Studio build plates that open already colored, with tests that prove the parts print, fit and assemble. Use when designing, changing, or adding printable parts, brackets, mounts, enclosures, jigs, models, multi-color (AMS) prints, build plates, or STEP files, even if the user doesn't say "build123d" or "CAD". Part of claude-cad; examples in examples/fit-coupon (small) and examples/near-ceiling-track (room-sized).
---

# Parametric 3D-print CAD (build123d + cadkit)

You design physical, 3D-printed things as Python code. The CAD tool (Onshape, FreeCAD, Fusion) is for looking, so
export real B-rep **STEP**, not meshes. The slicer gets **3MF** build plates that open ready to print. The default
printer is a Bambu A1 (256 × 256 mm bed, 0.4 mm nozzle, 0.2 mm layers) printing PETG; it's a `cadkit.Printer`, so
change it in one place.

Read before you start:

- `references/build123d-patterns.md` before writing geometry: tested snippets and the traps that cost time.
- `references/printing.md` before plates, colors or anything the slicer sees: Bambu project 3MF, AMS rules,
  supports and bridges, checking a file through Bambu Studio's own CLI.
- `references/lessons.md` when planning: what went wrong on a room-sized build and the rule it turned into.

Use **cadkit** (`cadkit/` in the claude-cad repo) instead of rewriting its pieces: print checks, clash finder,
two-color paint, plate packing, Bambu plate writer, slicer checks, viewer. `examples/fit-coupon/` is the smallest
complete project (copy it to start one); `examples/near-ceiling-track/` shows everything at scale.

## Project layout

```
<project>/
  pyproject.toml          uv project; Python 3.12 (newer Pythons may lack build123d's OCP wheels); build123d==0.13.0;
                          cadkit as a path dependency: [tool.uv.sources] cadkit = { path = "...", editable = true }
  <pkg>/params.py         every dimension in one frozen dataclass `Params` + default `P`, including the
                          `cadkit.Printer` and the filament (AMS slot) per color; nothing else hard-codes a size
  <pkg>/layout.py         pure math (no CAD): positions, spacings, validation; fast to test
  <pkg>/joints.py         this project's joints sized from params, on cadkit.shapes (rect, poly, bowtie, dovetail)
  <pkg>/parts/<part>.py   make(p, ...) -> Part in PRINT orientation; place(p, ...) -> Location into the assembly frame
  <pkg>/assembly.py       placed_parts() -> [(name, Part)]; cadkit.clash.find_clashes over them
  <pkg>/plates.py         kits -> cadkit.plates.pack -> Plate(name, qty, items); dedupe kits by a geometry key
  <pkg>/build.py          CLI: all | parts | plates | check | show ...; plates via cadkit.export.write_plates
  tests/                  pytest, one file per part + layout/assembly/plates/build
  docs/specs/             design spec, with an "Amendments" section per change of decision
  docs/measurements.md    real-world measurements, each with where it was measured from
  out/                    generated, gitignored
```

Run with `uv run python -m <pkg>.build ...`. Test with `uv run pytest -n auto -m "not slow"` while iterating and the
full `uv run pytest -n auto` before committing. Mark minutes-long tests `@pytest.mark.slow` and run long suites in
the background.

## Workflow

1. **Sketch before code.** Settle shape and proportions with quick inline SVG sketches (side, end and plan views),
   offering 2–3 options with a recommendation. People correct a picture much faster than prose.
2. **Measure the real world first** when the thing mounts on it (walls, desks, machines). Record each measurement
   with the end it was taken from. Check that the measurements close (opposite walls agree, segments sum to the
   total). If they don't, say which reading to retake; if repeated readings agree, the room isn't square: model it
   square and absorb the difference in parts that are cut to fit anyway.
3. **Spec, then build.** Write the agreed design to `docs/specs/`. Prototype risky geometry in a scratch copy first.
   Record every later change of mind as an amendment.
4. **Test first for every part.** Write the failing test, implement, watch it pass. Expectations come from params.
   At minimum, with cadkit.checks:
   - `printable_problems(part, p.printer) == []`: one valid solid, flat on Z = 0, inside the bed;
   - `open_edges(part) == 0`: watertight mesh;
   - `off_layer_z(part, p.printer) == []`: tops and color seams on layer boundaries;
   - two colors: `unsupported(upper, lower) == 0`: the upper color never starts over air;
   - a dimension test of the key features (probe with thin boxes, measure the pieces);
   - after any cut through a part, still `printable_problems == []` (one solid: a cut didn't sever it).
5. **The assembly clash test is the backbone.** Place every part and require pairwise intersection volume ≈ 0
   (`cadkit.clash.find_clashes`). Make sure it can fail:
   - add a "too tight" variant that must report clashes;
   - model the environment (walls, ceiling, doors) as solids, including walls you leave out of the render;
   - model moving things as swept envelopes (e.g. the longest car on the tightest curve);
   - model installed hardware (rods, wires, screws, cables) as solids, and the paths they need (a wire through a
     groove) as solids that must touch nothing.
6. **Look at it.** Render previews (`cadkit.export.write_svg` → `rsvg-convert` → PNG) or the viewer, and look before
   saying a part is right. Eyes catch things tests don't: a stray tip poking out of a corner passed every test.
7. **Check what the slicer sees.** When plate or 3MF code changes, run the plates through Bambu Studio's CLI
   (`cadkit.bambu.roundtrip`, `slice_report`): same filament per part, same geometry per object, one color change
   per plate. Unit tests passed while Bambu showed every part green and three different ladders as one.
8. **Independent review before printing.** A fresh reviewer agent checks print orientation, overhangs and bridges
   (`cadkit.checks.downward_faces`), thin walls, mating fits and assembly order, and must prove each finding with a
   probe. Fix real findings test-first.
9. Commit after each chunk of work.

## Design rules

- **Print flat, no supports.** Make parts 2D profiles extruded to a thickness. Put features that flex (snaps,
  latches) in the print plane, so they bend along the layers. Openings that must face down print as shallow arcs,
  or get turned so they open upward. Holes that must be truly round go in the print plane.
- **Nothing starts over air.** A face that faces down above the bed is a bridge or needs support. Watch for a
  feature sitting over another part's hole: a tie plate over the slot for a tab bridged 3.4 mm of nothing. Clip the
  upper feature to what's under it, or leave the hole open to the sky.
- **Snap or slot to locate; glue only for strength.** Use tabs and slots, bow-tie keys, half-laps, latches and
  jigsaw joints. Glue only where gravity or vibration works against a slide fit. Take clearances from params
  (`fit_slide`, `fit_snap`) and tune them with a printed **fit-test coupon** (`examples/fit-coupon`).
- **Half-laps carry load both ways.** Split the depth about 50/50 between the two parts. A 1 mm notch against a
  full-depth slot leaves the slotted part mostly hollow.
- **Don't notch a tension member.** Cut notches into members in compression (or solid blocks), never the chord being
  pulled apart.
- **Grooves keep a floor.** A wire or cable groove cut full depth through every member that crosses it can leave the
  part held together by a sliver. Cut it from the top over a floor of a few layers.
- **Split long things under the bed size**, at the strongest joints, and run a continuous member (rail, rod)
  across the splits.
- **Z levels on layer multiples.** Tops, color seams and inlays at multiples of the layer height (0.2 mm), or the
  slicer splits a layer.
- **Multi-color (AMS) prints: one color change per plate.** Make color regions separable by height: one color up to
  a Z, the other above it. Model a two-color part as a Compound of two colored, labeled bodies (e.g. `x_wood`,
  `x_steel`). Two-color parts never share a plate with single-color parts (`cadkit.plates.pack` does this).
  Filaments per color live in params and match the user's AMS slots.
- **Parameters, not numbers.** A user's change should be a one-line edit in `params.py`, and tests derive their
  expectations from params.
- **Validate inputs loudly** (e.g. `validate_bays` raises with the bad value and the allowed range).
- **Real-world checks:** sag under load, thermal gaps, real stock lengths, metal springback (a bending jig is a
  gauge, not a form), screw size against slot size, and which way each part has to go in during assembly.

## Outputs

- `out/step/*.step`: one per distinct part, labeled (`shape.label`) so CAD shows real names. In assemblies, label
  base shapes by part type, since STEP dedups shared shapes and per-instance names collide. Two-color parts are
  one painted solid (`cadkit.paint`). A whole room is ~200 MB; upload the plain STEP to Onshape, not a zip.
- `out/plates/*.3mf` + `.step` and `plates.csv` (plate, quantity, contents) from `cadkit.export.write_plates`:
  each 3MF is a Bambu Studio project with a filament per part, so it opens colored (File → Open Project).
- `out/manifest.csv` (part, quantity), and for things that mount: a measurement sheet (CSV, mm and inches) for
  marking walls and ceilings, and cut lengths for any stock.

## Viewing

- **OCP CAD Viewer** shows build123d objects directly, with no STEP translation.
  - Start it with `uv run python -m ocp_viewer --port 3939`.
  - Open `http://127.0.0.1:3939/viewer` **before** sending, since only connected tabs receive models.
  - Send with `cadkit.view.show(shape)` or a `build show <target>` command. If the tab still shows the old model,
    reload it and send again; huge sends can drop the connection.
- **Onshape** (Create → Import) for measuring and fine detail. Translating a big STEP takes minutes. An Onshape MCP
  connector, if present, is FeatureScript-only and spends the account's API allowance: say so before using it.
- **Share a 3D preview** as a page: export glTF per section and load it with three.js (see the room viewer in
  `examples/near-ceiling-track/web/`).

## Working with the user

- When they send a screenshot (slicer, CAD), identify what's in it by counting features (posts, ties, holes) and
  their spacing against the model's numbers before changing anything. "Move it one tie left in my picture" means
  working out which way the picture's left is in model coordinates.
- Learn their words for parts ("nubs" for tabs, "decks" for ladders) and use them back.
- When a measurement doesn't close, tell them which one to retake, and accept "I measured it three times".
