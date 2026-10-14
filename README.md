# train-ho-scale

A 3D-printable HO-scale track shelf that runs around a room near the ceiling, plus **print-cad**: the Claude Code
skill and method used to design it.

**Parametric, test-driven CAD for 3D printing, written in Python.** Parts are code
([build123d](https://github.com/gumyr/build123d)). The build exports real CAD (**STEP**) for Onshape/FreeCAD/Fusion,
and ready-packed slicer plates (**3MF**). Tests prove every part prints flat with no supports, is watertight,
and fits and assembles with its neighbors.

The repo has two parts:

1. **A [Claude Code](https://claude.com/claude-code) skill** (`.claude/skills/print-cad/`) that teaches Claude this
   way of working: how to lay out a project, the test-first workflow, the design rules for printable snap-together
   parts, multi-color (AMS) printing, and the build123d traps that cost time.
2. **A complete worked example** (`demo/near-ceiling-track/`): an HO-scale model railroad shelf that runs around a
   room 12" below the ceiling. Deck-truss straight runs, pony-truss corners on bent aluminum rods, wall brackets,
   tie ladders, a fit-test coupon, ~200 tests.

```
.
├── .claude/skills/print-cad/      the Claude Code skill
│   ├── SKILL.md                   workflow, design rules, outputs, viewing
│   └── references/
│       └── build123d-patterns.md  tested snippets and traps (build123d 0.13)
├── demo/near-ceiling-track/       worked example (its own uv project)
│   ├── README.md                  build, view, print, install, tests
│   ├── docs/                      overview, specs (with amendment logs), measurements
│   ├── hotrain/                   the parametric model
│   └── tests/
├── CLAUDE.md                      working notes for Claude Code sessions in this repo
├── LICENSE                        MIT
└── README.md
```

## Requirements

| What | Why | Get it |
|---|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Installs Python 3.12 and every dependency per project | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (macOS/Linux) or `brew install uv` |
| A slicer that reads 3MF | Printing | Bambu Studio, OrcaSlicer, PrusaSlicer |
| CAD that imports STEP (optional) | Measuring and fine detail | Onshape (free plan), FreeCAD, Fusion |
| `rsvg-convert` (optional) | Turning SVG previews into PNGs | `brew install librsvg` / `apt install librsvg2-bin` |
| [Claude Code](https://claude.com/claude-code) (optional) | Using the skill | — |

Developed on macOS (Apple Silicon). build123d's OCP wheels exist for macOS, Linux and Windows on Python 3.12, which
is why each project pins 3.12. A newer system Python doesn't matter, because uv fetches 3.12 itself.

## Quick start (the demo)

```bash
git clone https://github.com/jasondouglascox-coder/train-ho-scale.git
cd train-ho-scale/demo/near-ceiling-track
uv sync                                                          # first run downloads Python 3.12 + build123d (~1-2 min)
uv run pytest -n 6 -m "not slow"                                 # ~2 min, should be all green
uv run python -m hotrain.build starter --run-style deck_truss     # out/starter/: one 16" bay + fit-test coupon
```

Open `out/starter/*.3mf` in your slicer. **Print `fit_test.3mf` first**: it calibrates the snap and slide fits for
your printer. Everything else (more outputs, the 3D viewer, the install order, adapting it to your room) is in
[demo/near-ceiling-track/README.md](demo/near-ceiling-track/README.md).

## Using the skill

- **In this repo:** open the repo in Claude Code. Project skills in `.claude/skills/` load automatically, and Claude
  uses `print-cad` whenever you ask it to design or change printable parts.
- **In your other projects:** copy or symlink it into your user skills.

  ```bash
  mkdir -p ~/.claude/skills
  ln -s "$PWD/.claude/skills/print-cad" ~/.claude/skills/print-cad
  ```
- **Starting a new design:** ask Claude something like *"use print-cad to design a wall bracket for X"*. Expect quick
  sketches and 2–3 options first, then a spec, then parts built test-first, preview renders, and finally an
  independent review before you print. `demo/near-ceiling-track` is the reference for the project layout it creates.

## The approach in one screen

- **Every dimension lives in one `params.py`.** A design change is a one-line edit, and tests derive their
  expectations from the params rather than hard-coded numbers.
- **Parts print flat with no supports.** They're 2D profiles extruded to a thickness, made in print orientation and
  placed into the assembly by a separate transform.
- **Snap or slot to locate, glue only for strength.** Tabs, bow-tie keys, half-laps and latches, with clearances
  tuned by a printed fit-test coupon.
- **The assembly clash test is the backbone.** It includes the room (walls, ceiling, doors), moving envelopes (the
  longest car on the tightest curve) and the hardware (rods, wires, screws), and it has a variant that must fail.
- **Multi-color without the waiting.** Two-color parts change color once, at a layer boundary, and never share a
  plate with single-color parts. The 3MF has one object with a part per color, and the STEP has one solid with
  painted faces.
- **Look before you trust.** Preview renders and a 3D viewer, because some mistakes pass every test.

## Viewing

- **OCP CAD Viewer** shows the models without any STEP translation.
  - Start it with `uv run python -m ocp_viewer --port 3939`.
  - Open http://127.0.0.1:3939/viewer, then send a model (the demo uses `build show <target>`).
- **Onshape:** Create → Import with the plain `.step` (not zipped). Colors and part names come through.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `uv sync` fails on Python / OCP wheels | Run `uv python install 3.12`, then `uv sync` again. Don't change the 3.12 pin. |
| The viewer page is blank after sending | Open the page **before** sending; reload it and send again after very large models. |
| Onshape rejects the file | Upload the plain `.step`, not a zip. Large rooms take minutes to translate. |
| The slicer shows a ladder's gray tie plates on the bed | You're on an old build; current 3MFs keep each two-color part as one object. Rebuild. |
| Tests are slow | Use `-n <cores>` (pytest-xdist) and `-m "not slow"` while iterating; run the full suite before committing. |
| `UnicodeEncodeError` in tests | The process has an ASCII locale. Current code writes UTF-8 explicitly; set `LANG=en_US.UTF-8` for older checkouts. |

## Safety

The demo hangs on walls and a ceiling above people. Screw into studs where you can, use drywall anchors rated well
beyond the load where you can't, and check your own fixings. Mains-powered train controllers stay on the floor;
only low-voltage DC goes up to the track. No warranty (see LICENSE).

## License

[MIT](LICENSE). Use it, change it, print it, share it; keep the copyright notice.
