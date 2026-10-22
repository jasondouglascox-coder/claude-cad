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
- `examples/refill-spool/`: a ~87 g two-piece spool for Bambu refill coils (package `refill_spool`): spoked flanges,
  barrel with zip-tie strap tracks, screw-on cap, a key into the refill core's notch. Threads from `cadkit.shapes.thread`.
- `examples/sunflower-wall/`: a ~10" wall sunflower printed in one go (package `sunflower`, `flower.py`): lofted
  arched petals with orange valley beads, a domed Fibonacci head of diamond seeds, four colors by height.
- `examples/rose-wall/`: an 8" open rose printed in one go (package `rose_wall`): petals swept round the axis
  and trimmed to pointed lenses, curling past level (PETG-interface tree supports), a funnel centre, a keyhole.

## Commands

Each project runs from its own folder:

```bash
cd cadkit && uv sync && uv run pytest -n 4                       # ~10 s; includes a live Bambu Studio check if installed
cd examples/fit-coupon && uv sync && uv run pytest               # ~1 min
cd examples/near-ceiling-track && uv run pytest -n 6 -m "not slow"   # ~4 min; full suite ~25 min, run it in the background
cd examples/sunflower-wall && uv run pytest -n 3 --dist loadfile -m "not slow"   # whole flower ~12 GB a worker; slow: Bambu
cd examples/sharpie-colorizer && uv run pytest -n 4                  # ~30 s, both plates through Bambu
cd examples/refill-spool && uv run pytest -n 2                       # ~20 s, both halves through Bambu
cd examples/rose-wall && uv run pytest -m "not slow"                  # ~4 min (fusing the petals); slow: Bambu
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
- `out/` is generated and gitignored. Never commit it.
- Decisions live in each project's `docs/specs/*.md` with an Amendments section. **Add an amendment whenever a
  decision changes.** Real-world measurements go in `docs/measurements.md`, with where each was measured from.
