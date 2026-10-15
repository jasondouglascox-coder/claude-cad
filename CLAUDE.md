# claude-cad: working notes for Claude Code

## What's here

- `.claude/skills/print-cad/`: the skill. **Use it for any part design or change.** Read
  `references/build123d-patterns.md` before writing geometry and `references/printing.md` before touching plates,
  colors or 3MF output.
- `cadkit/`: the shared library (its own uv project). Projects depend on it by path, editable. Generic code goes
  here, project code stays in the project. A helper two projects would both want belongs in cadkit, with a test in
  `cadkit/tests/`.
- `examples/fit-coupon/`: the smallest complete project; the template for new ones.
- `examples/near-ceiling-track/`: the HO railroad (package `hotrain`). It has its own `CLAUDE.md`; read it when
  working there.
- `examples/sunflower-wall/`: a 400 mm wall sunflower (package `sunflower`): lofted arched petals in quarters, a
  Fibonacci seed head of ~1,200 cones, snap pins.

## Commands

Each project runs from its own folder:

```bash
cd cadkit && uv sync && uv run pytest -n 4                       # ~10 s; includes a live Bambu Studio check if installed
cd examples/fit-coupon && uv sync && uv run pytest               # ~1 min
cd examples/near-ceiling-track && uv run pytest -n 6 -m "not slow"   # ~4 min; full suite ~25 min, run it in the background
cd examples/sunflower-wall && uv run pytest -n 6 -m "not slow"       # ~2 min; slow tests slice every plate in Bambu
```

## Rules

- **Test first:** write the failing test, implement, then watch it pass. Tests derive expectations from `params.py`;
  no magic numbers.
- **Print rules** are enforced by tests with `cadkit.checks`: flat, one solid, no supports, watertight; Z levels on
  layer multiples; the upper color never over air; at most one color change per plate. Keep them green.
- **When plate or 3MF output changes**, run the plates through Bambu Studio's CLI (`cadkit.bambu`): same filaments,
  same geometry per object, one color change. Unit tests alone have missed three real slicer bugs.
- **After a visible change**, render it (SVG/PNG or the viewer) and look at it before saying it's right.
- **Before printing a new batch**, run an independent review of the changed parts: print orientation, bridges
  (`cadkit.checks.downward_faces`), thin walls, mating fits and assembly order.
- `out/` is generated and gitignored. Never commit it.
- Decisions live in each project's `docs/specs/*.md` with an Amendments section. **Add an amendment whenever a
  decision changes.** Real-world measurements go in `docs/measurements.md`, with where each was measured from.
