# Spot Save: sunflower 10" one-piece (2026-10-16)

To the next Claude session on another machine: read this first, then delete this file once you've picked the work
up (commit the deletion).

## Where things stand

**Done, tested, and pushed: the 16" kit** (`examples/sunflower-wall`, package `sunflower`). All 47 tests pass, and
Bambu Studio slices every plate.
- 400 mm flower.
- 4 back + 4 front arched petal quarters, with 9 lengthwise vein grooves per petal.
- A one-piece domed seed head: 1,177 diamond seeds (Voronoi cells of a Vogel spiral, pyramid tops, 7 mm dome).
- 8 snap pins + 4 spares, and a keyhole in each back quarter.
- An Onshape assembly STEP (`build step`).
- Spec: `examples/sunflower-wall/docs/specs/2026-10-15-sunflower-design.md`, with an amendment log.

**In progress, NOT verified: the 10" one-piece print** (`examples/sunflower-wall/sunflower/small.py`,
`tests/test_small.py`).
- Ask: the same flower at the biggest size the A1 bed takes (~250 mm), every part stacked in place and printed in
  one go.
- Don't re-architect: the 16" stays the main design, and the user will want to tweak it later.
- Wall: a 20 3/8" vertical gap, with the nail 8" down from its top (`docs/measurements.md`). The flower must hang
  centered, so the nail sits 2 3/16" = 55.56 mm above the flower's center. The keyhole slot's top is placed so a
  3 mm nail shank rests exactly there. The user said they'd move the nail if that isn't possible; it looked
  possible.

What `small.py` does:
- `params()` scales the radii and widths only. Thicknesses, petal_min and seed size stay the same. center_t and
  seed_dome are scaled to layer multiples, and the 45° bevel is kept.
- Front petals are filled down to the bed. They would otherwise start over air above the arching back petals.
- The seed head sits on a hidden yellow riser just above the tallest yellow. Black never shares a layer with
  yellow, so the colors stack yellow → black → brown: 2 color changes. Sharing layers would cost about 60
  swaps.
- No pins or sockets: `center.assembled(p, sockets=False)` and `quarter.whole(p, layer)` were added for this.
- One keyhole behind the first front petal's root, with a 45° tapered roof (no bridge).
- `plan()` / `write()` put the whole flower on one plate, as one object with 3 parts on filaments 2/3/4.

Status of the tests:
- Only `test_biggest_flower...` and `test_nail_height...` have passed.
- The geometry tests have never completed: the run was stopped for memory (see below), then the session ended.
- Expect to debug: the yellow union (two whole rings + fill + riser), the keyhole taper extrude on a stadium
  sketch, `downward_faces` limits, and whether the keyhole cavity stays inside solid material.

**Also done (in cadkit):**
- `write_settings`: Bambu project settings for the user's AMS.
- `cadkit.render`: shaded PNG previews.
- `is_multi_color`: parts with 3+ colors stacked by height, checked in Bambu.

## Next steps

1. `cd examples/sunflower-wall && uv sync && uv run pytest -p no:xdist tests/test_small.py -m "not slow"`.
   Fix it until green.
2. Render it (`cadkit.render.render` on `small.make(small.params()).children` with their colors) and look at it.
   Show the user a front and an iso view.
3. Add a `build small` command that writes `out/small/` (plate 3MF, STEP, renders).
4. Run the slow test `test_bambu_slices_it_yellow_then_black_then_brown`. Report grams and time from
   `bambu.slice_report`.
5. Run an independent review before the user prints: overhangs, the keyhole, the riser hidden under the head's
   bevel, thin walls.
6. Add a spec amendment for the 10" version, update the README, commit, and push.

## How this user works (from this machine's memory)

- **Memory:** don't run heavy CAD tests in many parallel processes. Each pytest-xdist worker builds its own copy
  of the whole model. Use `-p no:xdist` or at most `-n 2` for whole-model tests, don't build or render while a
  suite runs, and keep booleans away from thousand-solid compounds (a clash test once died at exit 137).
- **Baby steps:** fix only what they list, show a render fast, iterate.
- **Commits:** commit after each natural chunk of work without asking, and push freely in claude-cad.
- **Tone:** be direct and concise. Don't use "honestly" framing.
- **Colors:** AMS slots are 1 orange, 2 yellow, 3 black, 4 brown, all PLA. Orange is parked: the user didn't like
  the orange-top renders.
