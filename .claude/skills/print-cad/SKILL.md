---
name: print-cad
description: Parametric, test-driven CAD for 3D-printed parts in Python (build123d), exported as STEP for Onshape/other CAD and as ready-packed 3MF build plates for the slicer, with tests that prove the parts print, fit and assemble. Use when designing, changing, or adding printable parts, brackets, mounts, model-railroad structures, multi-color (AMS) prints, build plates, or STEP files, even if the user doesn't say "build123d" or "CAD". Worked example: demo/near-ceiling-track.
---

# Parametric 3D-print CAD (build123d → STEP + 3MF)

You design physical, 3D-printed things as Python code. The CAD tool (Onshape, FreeCAD, Fusion) is for looking,
so export real B-rep **STEP**, not meshes. The slicer gets **3MF** build plates. The default printer is
a Bambu A1 (256 × 256 mm bed, 0.4 mm nozzle, 0.2 mm layers) printing PETG; keep these as parameters.

Read `references/build123d-patterns.md` before writing geometry code. It has tested snippets and the traps that
cost time. For a complete example of everything below, read `demo/near-ceiling-track/` (start with its README and
`docs/overview.md`).

## Project layout

```
<project>/
  pyproject.toml          uv project; pin Python 3.12 (newer Pythons may lack build123d's OCP wheels); build123d==0.13.0
  <pkg>/params.py         every dimension in one frozen dataclass `Params` + default `P`; nothing else hard-codes a size
  <pkg>/layout.py         pure math (no CAD): positions, spacings, validation; fast to test
  <pkg>/joints.py         shared 2D shapes: rect(), poly() (forces CCW), keys, dovetails
  <pkg>/checks.py         printable_problems(part) -> list[str]
  <pkg>/parts/<part>.py   make(p, ...) -> Part in PRINT orientation; place(p, ...) -> Location into the assembly frame
  <pkg>/assembly.py       placed_parts() -> [(name, Part)], find_clashes(), make() -> labeled Compound
  <pkg>/plates.py         bed packing (MaxRects), kits, dedupe -> plates
  <pkg>/paint.py          two-color parts: one solid in CAD with face colors in the STEP
  <pkg>/build.py          CLI: all | parts | assembly | plates | check | show ...
  tests/                  pytest, one file per part + layout/assembly/plates/build
  docs/specs/             design spec, with an "Amendments" section per change of decision
  out/                    generated, gitignored
```

Run with `uv run python -m <pkg>.build ...`. Test with `uv run pytest -n auto -m "not slow"` while iterating, and the
full `uv run pytest -n auto` before committing. Use pytest-xdist, mark minutes-long tests `@pytest.mark.slow`, and run
long suites in the background.

## Workflow

1. **Sketch before code.** Settle shape and proportions with quick inline SVG sketches (side, end and plan views),
   offering 2–3 options with a recommendation. People correct a picture much faster than prose.
2. **Spec, then build.** Write the agreed design to `docs/specs/`. Prototype risky geometry in a scratch copy first.
   Record every later change of mind as an amendment.
3. **Test first for every part.** At minimum:
   - `printable_problems(part) == []`: one valid solid, flat on Z = 0, inside the bed;
   - a dimension test of the key features (probe with thin boxes and measure the intersection);
   - a watertight-mesh check: every tessellation edge shared by exactly two triangles.
4. **The assembly clash test is the backbone.** Place every part and require pairwise intersection volume ≈ 0
   (bbox prefilter first). Make sure it can fail:
   - add a "too tight" variant that must report clashes;
   - model the environment (walls, ceiling, doors) as solids;
   - model moving things as swept envelopes (e.g. the longest car on the tightest curve);
   - model installed hardware (rods, wires, screws, cables) as solids.
5. **Look at it.** Render previews (`project_to_viewport` → SVG → PNG) and read the image before saying a part is
   right. Show the user. Eyes catch things tests don't: a stray tip poking out of a corner passed every test.
6. **Independent review before printing.** A fresh reviewer agent checks print orientation, overhangs, thin walls,
   mating fits and assembly order, and must prove each finding with a probe. Fix real findings test-first.
7. Commit after each chunk of work.

## Design rules

- **Print flat, no supports.** Make parts 2D profiles extruded to a thickness. Put features that flex (snaps,
  latches) in the print plane, so they bend along the layers. Openings that must face down print as shallow arcs,
  or get turned so they open upward.
- **Snap or slot to locate; glue only for strength.** Use tabs and slots, bow-tie keys, half-laps, latches and
  jigsaw joints. Glue only where gravity or vibration works against a slide fit. Take clearances from params
  (`fit_slide`, `fit_snap`, `fit_thread`) and tune them with a printed **fit-test coupon** (3 variants of each joint,
  marked with 1/2/3 notches).
- **Half-laps carry load both ways.** Split the depth about 50/50 between the two parts. A 1 mm notch against a
  full-depth slot leaves the slotted part mostly hollow.
- **Don't notch a tension member.** Cut notches into members in compression (or solid blocks), never the chord being
  pulled apart.
- **Split long things under the bed size**, at the strongest joints, and run a continuous member (rail, rod)
  across the splits.
- **Z levels on layer multiples.** Tops, color seams and inlays at multiples of the layer height (0.2 mm), or the
  slicer splits a layer.
- **Multi-color (AMS) prints: one color change per plate.** Make color regions separable by height: one color up to
  a Z, the other above it. Two-color parts never share a plate with single-color parts. Pool two-color parts onto
  their own plates, and write each as ONE 3MF object with one part per color, or the slicer drops the upper color
  onto the bed.
- **Parameters, not numbers.** A user's change should be a one-line edit in `params.py`, and tests derive their
  expectations from params.
- **Validate inputs loudly** (e.g. `validate_bays` raises with the bad value and the allowed range).
- **Real-world checks:** sag under load, thermal gaps, real stock lengths, metal springback (a bending jig is a
  gauge, not a form), screw size against slot size, and which way each part has to go in during assembly.
  Measure the real wall (stud positions, door trim, headers) before final layouts.

## Outputs

- `out/step/*.step`: one per distinct part, labeled (`shape.label`) so CAD shows real names. In assemblies, label
  base shapes by part type, since STEP dedups shared shapes and per-instance names collide. A whole room is ~200 MB.
  Upload the plain STEP to Onshape; it rejects zipped STEP.
- Colored review models: set `shape.color`. Two-color printed parts are one painted solid in the STEP.
- `out/plates/*.3mf` + `.step` and `plates.csv` (plate, quantity, contents); `out/manifest.csv` (part, quantity).
- A measurement sheet (CSV, mm and inches) for marking walls and ceilings, and rod cut lengths.

## Viewing

- **OCP CAD Viewer** shows build123d objects directly, with no STEP translation.
  - Start it with `uv run python -m ocp_viewer --port 3939`.
  - Open `http://127.0.0.1:3939/viewer` **before** sending, since only connected tabs receive models.
  - Send with `set_port(...)` then `show(...)`, or a `build show <target>` command. Reload the tab if a huge send
    loses the connection.
- **Onshape** (Create → Import) for measuring and fine detail. Translating a big STEP takes minutes. An Onshape MCP
  connector, if present, is FeatureScript-only and spends the account's API allowance: say so before using it.
