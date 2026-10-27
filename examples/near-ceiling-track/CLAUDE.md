# near-ceiling-track: working notes for Claude Code

The HO track shelf, a uv project with package `hotrain`, built on `cadkit` (`../../cadkit`).

- Start with `README.md` and `docs/overview.md`.
- Decisions live in `docs/specs/*.md`, each with an Amendments section. **Add an amendment whenever a decision
  changes.**
- Real wall measurements live in `docs/measurements.md`. Add new ones there, with which end each was measured from.
  The room is 3/8" out of square (front wall short); the model is square and `Room.misfit()` keeps the difference.

## Commands

Run everything from this folder:

```bash
uv sync
uv run pytest -n 6 -m "not slow"     # while iterating, ~4 min
uv run pytest -n 6                   # before every commit, ~25 min; run it in the background
uv run python -m hotrain.build sections --run-style deck_truss   # out/sections: the room a bay at a time, plus the corner kits
uv run python -m hotrain.build show room --run-style deck_truss   # OCP viewer: start it and open the page first
uv run python -m hotrain.build room --run-style deck_truss        # out/step/office.step for Onshape
uv run python -m hotrain.build web --run-style deck_truss         # out/web: the shareable 3D room viewer
uv run python -m hotrain.build render --run-style deck_truss      # out/render/*.png (~11 min); docs/images/ are copies
```

- Straight runs use **`--run-style deck_truss`** (the chosen look); the params default is still `arch`. Corners
  default to `pony`.
- Filaments (the user's AMS): `filament_gray` 1 (PETG), `filament_brown` 2 (PETG), `filament_white` 3 (PLA, ceiling
  cleats). Plates open colored in Bambu Studio; the slow tests check that through its CLI.
- The user's words: "nubs" are the truss tabs, "decks" are the tie ladders, "power cuts"/"wire gaps" are the solder
  gaps (one per bay, in the middle ladder).
