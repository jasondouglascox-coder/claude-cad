# claude-cad: working notes for Claude Code

## What's here

- `.claude/skills/print-cad/`: the skill. **Use it for any part design or change.** Read
  `references/build123d-patterns.md` before writing geometry and `references/printing.md` before touching plates,
  colors or 3MF output.
- `cadkit/`: the shared library (its own uv project). Projects depend on it by path, editable. Generic code goes
  here, project code stays in the project. A helper two projects would both want belongs in cadkit, with a test in
  `cadkit/tests/`.
- `examples/fit-coupon/`: the smallest complete project; the template `cadkit.new` copies for new ones.
- **The user's setup is settings, not code:** `cadkit.settings` (printer bed/layer/nozzle, colors, color-change
  budget, slicer, projects folder) from `CADKIT_*` variables or an untracked `cadkit.toml`. With nothing set it's the
  Bambu A1 + 4-color AMS + Bambu Studio setup everything was built on, and outputs must stay identical for it.
  Check with `cd cadkit && uv run python -m cadkit.settings`. New projects go in `settings().projects`.
- Slicers sit behind `cadkit.slicers` (Bambu built in); projects and tests use `slicers.active()`, never
  `cadkit.bambu` directly. Adding one: `CONTRIBUTING.md`.
- `examples/near-ceiling-track/`: the HO railroad (package `hotrain`). It has its own `CLAUDE.md`; read it when
  working there.
- `examples/candle-adapter/`: a one-piece black adapter (package `candle`) that holds a 20 mm candle in a flat
  chandelier cup.
- `examples/sharpie-colorizer/`: an inline Sharpie colorizer for the A1's external-spool guide tube (package
  `sharpie_colorizer`): a snap clip on the 40 × 20 frame bar and a block holding three tilted markers; fit-test
  plate first.
- `examples/refill-spool/`: a ~89 g two-piece spool for Bambu refill coils (package `refill_spool`): spoked flanges,
  barrel with zip-tie strap tracks, screw-on cap, a key into the refill core's notch. Threads from `cadkit.shapes.thread`.
- `examples/sunflower-wall/`: a ~10" wall sunflower printed in one go (package `sunflower`, `flower.py`): lofted
  arched petals with orange valley beads, a domed Fibonacci head of diamond seeds, four colors by height.
- `examples/rose-wall/`: an 8" open rose printed in one go, or four 4" ones a plate (`params.small`) (package `rose_wall`): petals swept round the axis
  and trimmed to pointed lenses, curling past level (PETG-interface tree supports), a funnel centre, a keyhole.
- `examples/peony-wall/`: an 8" tight peony, soft pink, no supports (package `peony_wall`): 81 freeform ruffled
  petals, each resting on the one below through a hidden 45-degree fill, built as meshes and unioned with
  `cadkit.mesh` (B-rep booleans gave up); a yellow stamen insert pushed in from the back.
- `examples/lily-wall/`: a 180 mm lily (package `lily_wall`): six arched, recurved mesh tepals, white fading to
  purple by height through 40 dithered layers (21 swaps), tree supports in the loaded PLA.
- `examples/lily-of-the-valley/`: a 188 mm arching sprig (package `lily_of_the_valley`): five white bells with
  scalloped, curled rims, white to the wall, on a green stem of 4 mm half-ovals: coloured by part (20 swaps), no
  supports: bells are tubes of sections round on top over a hidden 46-degree fill, the rest domes (`shapes.py`).
  Two to a plate, the second mirrored.
- `examples/lamp-chimney/`: a white replacement for a lamp's broken glass chimney (package `lamp_chimney`): Ø40
  foot into the gallery's spring tabs, one-line (0.42 mm) wall, rounded 45-degree shoulder to a Ø26 neck,
  131 mm; printed in spiral (vase) mode over a solid foot, brims inside and out, set in the project.
- `examples/halloween-gnome/`: a 2" witch-hat gnome (package `halloween_gnome`) with a 1/2" hole to sit on a mini
  Christmas tree: body, hat and pink nose printed apart (2 swaps each by height) and pressed together with no
  clearance; every body a stack of horizontal mesh sections, no supports.
- `examples/mini-sunflower/`: a 3" wall sunflower, four to a plate (package `mini_sunflower`): 24 pointed yellow
  petals, a raised brown ring of spiral diamonds round a sunk black eye, colours by height (2 swaps), no supports,
  a keyhole under the head; meshes from point grids.
- `examples/circle-jig/`: a trammel for marking circles of 2"–20" radius in four exact quarters (package
  `circle_jig`): a pinwheel whose bar and three short arms each have a straight edge on a line through the pivot
  screw; the bar prints as a hub piece and an extension that dovetails into it, each across its own plate.

## Commands

Each project runs from its own folder:

```bash
cd cadkit && uv sync && uv run pytest -n 4                       # ~10 s; includes a live Bambu Studio check if installed
cd examples/fit-coupon && uv sync && uv run pytest               # ~1 min
cd examples/near-ceiling-track && uv run pytest -n 6 -m "not slow"   # ~4 min; full suite ~25 min, run it in the background
cd examples/sunflower-wall && uv run pytest -n 3 --dist loadfile -m "not slow"   # whole flower ~12 GB a worker; slow: Bambu
cd examples/sharpie-colorizer && uv run pytest -n 4                  # ~30 s, both plates through Bambu
cd examples/refill-spool && uv run pytest -n 2                       # ~20 s, both halves through Bambu
cd examples/rose-wall && uv run pytest -n 4 -m "not slow"             # ~12 min, both sizes (fusing petals); slow: Bambu
cd examples/peony-wall && uv run pytest -n 4 -m "not slow"            # ~40 s; slow (-n 6, ~3 min): every petal, Bambu
cd examples/lily-wall && uv run pytest -n 6                           # ~30 s, through Bambu
cd examples/lily-of-the-valley && uv run pytest -n 6                  # ~15 s, through Bambu
cd examples/lamp-chimney && uv run pytest -n 4                       # ~15 s, through Bambu
cd examples/circle-jig && uv run pytest -n 6                         # ~40 s, both plates through Bambu
cd examples/halloween-gnome && uv run pytest -n 6                    # ~10 s, all three plates through Bambu
cd examples/mini-sunflower && uv run pytest -n 6                     # ~25 s, the plate through Bambu
```

## Rules

- **Test first:** write the failing test, implement, then watch it pass. Tests derive expectations from `params.py`;
  no magic numbers.
- **Print rules** are enforced by tests with `cadkit.checks`: flat, one solid, no supports, watertight; Z levels on
  layer multiples; the upper color never over air. Keep them green. **Color changes are a budget** (settings, default
  one per plate): when a design needs more, say so with the cost and alternatives, and record the accepted number
  per plate (`Plate(..., color_changes=n)`) and in the spec.
- **When plate or 3MF output changes**, run the plates through the slicer's CLI (`cadkit.slicers.active()`): same
  filaments, same geometry per object, the planned color changes. Unit tests alone have missed five real slicer bugs.
- **After a visible change**, render it (SVG/PNG or the viewer) and look at it before saying it's right. Every
  example's README opens with renders in `docs/images/` (a cadkit test checks); refresh them when the look changes.
- **Before printing a new batch**, run an independent review of the changed parts: print orientation, bridges
  (`cadkit.checks.downward_faces`), thin walls, mating fits and assembly order.
- `out/` is generated. The refill spool's is committed so a pull brings its print files: rebuild it and commit it
  with any change. Other projects' stay gitignored (the railroad's has a 208 MB STEP, over GitHub's 100 MB limit).
- Decisions live in each project's `docs/specs/*.md` with an Amendments section. **Add an amendment whenever a
  decision changes.** Real-world measurements go in `docs/measurements.md`, with where each was measured from.
