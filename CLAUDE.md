# train-ho-scale: working notes for Claude Code

## What's here

- `.claude/skills/print-cad/`: the project skill. **Use it for any part design or change**, and read
  `references/build123d-patterns.md` before writing geometry.
- `demo/near-ceiling-track/`: the HO track shelf, a uv project with package `hotrain`.
  - Start with its `README.md` and `docs/overview.md`.
  - Decisions live in `docs/specs/*.md`, each with an Amendments section. **Add an amendment whenever a decision
    changes.**
  - Real wall measurements live in `docs/measurements.md`. Add new ones there, with which end each was measured from.

## Working in the demo

Run everything from `demo/near-ceiling-track/`:

```bash
uv sync
uv run pytest -n 6 -m "not slow"     # while iterating, ~2 min
uv run pytest -n 6                   # before every commit, ~14 min; run it in the background
uv run python -m hotrain.build starter --run-style deck_truss
uv run python -m hotrain.build show room --run-style deck_truss   # OCP viewer: start it and open the page first
uv run python -m hotrain.build room --run-style deck_truss        # out/step/office.step for Onshape
```

- Straight runs use **`--run-style deck_truss`** (the chosen look); the params default is still `arch`. Corners
  default to `pony`.
- `out/` is generated and gitignored. Never commit it.
- **Test first:** write the failing test, implement, then watch it pass. Tests derive expectations from `params.py`;
  no magic numbers.
- **Print rules** are enforced by the tests:
  - flat, no supports, watertight;
  - Z levels on 0.2 mm multiples;
  - at most one color change per plate, with two-color parts as one 3MF object.
  Keep them green.
- After a visible change, render it (SVG/PNG or the viewer) and look at it before saying it's right.
- Before printing a new batch, run an independent review of the changed parts: print orientation, thin walls,
  mating fits and assembly order.
