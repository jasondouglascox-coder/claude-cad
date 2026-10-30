# claude-cad

> [!IMPORTANT]
> ## Requires Claude Opus 5.5 or higher
> **Use High effort or above.** The results here (geometry that prints first time, plates that open colored, tests
> that catch real slicer bugs) come from Opus 5.5 at High or higher effort. Smaller models or lower effort settings
> miss steps and produce parts that look right but don't print or fit. In Claude Code, pick the model and effort
> before you start (`/model`).

**Parametric, test-driven CAD for 3D printing, done with [Claude Code](https://claude.com/claude-code).** Parts are
Python ([build123d](https://github.com/gumyr/build123d)). The build exports real CAD (**STEP**) for
Onshape/FreeCAD/Fusion, and build plates for the slicer (**3MF**) that open in Bambu Studio already colored, one
filament per part. Tests prove every part prints flat with no supports, is watertight, puts color seams on layer
boundaries, and fits and assembles with its neighbors. Then Bambu Studio's own CLI checks the plates.

It was built for, and battle-tested on, a 3D-printed HO model railroad that runs around a whole room near the
ceiling (`examples/near-ceiling-track`). That project is the big example; the tool itself is generic. A smaller
one, a wall sunflower (`examples/sunflower-wall`), shows organic shapes and multi-color prints:

<img src="examples/near-ceiling-track/docs/images/bay_above.png" width="480" alt="One 16-inch deck-truss bay of the HO railroad shelf"> <img src="examples/sunflower-wall/docs/images/10in_front.png" width="320" alt="10-inch 3D-printed sunflower render">

```
.
├── .claude/skills/print-cad/      the Claude Code skill: how to work, design rules, lessons learned
│   ├── SKILL.md                   workflow, project layout, design rules, outputs, viewing
│   └── references/
│       ├── build123d-patterns.md  tested snippets and traps (build123d 0.13)
│       ├── printing.md            settings, supports, layers, color budgets, slicers, checking with the slicer's CLI
│       └── lessons.md             what went wrong on a room-sized build, and the rule each became
├── cadkit/                        the library every project imports (its own uv project, with tests)
├── examples/
│   ├── fit-coupon/                smallest complete project: start here; the template for `cadkit.new`
│   ├── candle-adapter/            one black part, glued into a chandelier cup
│   ├── refill-spool/              an 89 g screw-together spool for Bambu refills, threads and strap tracks
│   ├── grover-keychain/           a 4-color logo keychain traced from a raster, QR code on the back
│   ├── near-ceiling-track/        everything at scale: an HO railroad shelf around a room, ~220 tests
│   ├── sunflower-wall/            a 10" wall sunflower printed in one go, four AMS colors
│   └── rose-wall/                 an 8" open rose printed in one go, curled petals on PETG-interface supports
├── docs/specs/                    decisions about the tool itself
├── cadkit.toml.example            every setting for your printer/slicer/folder; copy to cadkit.toml (ignored)
├── CLAUDE.md                      working notes for Claude Code sessions in this repo
├── CONTRIBUTING.md                how to add a slicer or a setting
├── LICENSE                        MIT
└── README.md
```

## What you get

- **A skill that teaches Claude the method** (`print-cad`): sketch options first, spec with an amendment log, every
  dimension in one `params.py`, parts built test-first in print orientation, an assembly clash test that models the
  room and the hardware, renders you look at before trusting, the slicer as the last test, and an independent
  review before printing.
- **cadkit**, the parts every project needs and nobody should write twice:

  | Module | What it does |
  |---|---|
  | `cadkit.settings` | your setup (printer, colors, slicer, projects folder) from `CADKIT_*` variables or `cadkit.toml` |
  | `cadkit.printer` | `Printer(bed, bed_y, margin, layer, nozzle)`, defaults from your settings; `A1` |
  | `cadkit.shapes` | `rect`, `poly` (always counter-clockwise), `grow`, `bowtie` keys, `dovetail` jigsaw tabs |
  | `cadkit.checks` | `printable_problems`, `open_edges` (watertight), `off_layer_z`, `unsupported` (upper color over air), `downward_faces` (bridges) |
  | `cadkit.clash` | pairwise interference with a bounding-box prefilter |
  | `cadkit.paint` | two-color parts as one solid with face colors in the STEP; split bodies for viewers |
  | `cadkit.plates` | MaxRects bed packing (square or rectangular beds); multi-color parts on their own plates; `color_changes` counts a plate's swaps |
  | `cadkit.bambu3mf` | Bambu Studio project 3MF with a filament per part, plus readers for checking files |
  | `cadkit.bambu` | drive Bambu Studio's CLI: round-trip a plate, slice it, report filament per layer |
  | `cadkit.slicers` | one interface for any slicer: Bambu Studio built in, others [by PR](CONTRIBUTING.md#adding-a-slicer) |
  | `cadkit.render` | shaded, colored PNG previews (the pictures in every README) |
  | `cadkit.new` | start a project from the template in your projects folder |
  | `cadkit.export` | painted STEP plates + 3MF + `plates.csv`; hidden-line SVG previews |
  | `cadkit.view` | send shapes to OCP CAD Viewer |

- **Four examples**, each with pictures: a fit-test coupon (tune your printer's clearances, and the template for a
  new project), a candle adapter, a wall sunflower, and the railroad, which uses everything.

## Requirements

| What | Why | Get it |
|---|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Installs Python 3.12 and every dependency per project | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (macOS/Linux) or `brew install uv` |
| A slicer | Printing | Bambu Studio: tested, plates open colored and get sliced by the tests. Others (PrusaSlicer, Orca, Cura) load the geometry; set colors by hand, or [add yours](CONTRIBUTING.md#adding-a-slicer) |
| CAD that imports STEP (optional) | Measuring and fine detail | Onshape (free plan), FreeCAD, Fusion |
| `rsvg-convert` (optional) | Turning SVG previews into PNGs | `brew install librsvg` / `apt install librsvg2-bin` |
| [Claude Code](https://claude.com/claude-code) | Using the skill | — |

Developed on macOS (Apple Silicon). build123d's OCP wheels exist for macOS, Linux and Windows on Python 3.12, which
is why every project pins 3.12. A newer system Python doesn't matter, because uv fetches 3.12 itself.

## Quick start

```bash
git clone https://github.com/jasondouglascox-coder/claude-cad.git
cd claude-cad/examples/fit-coupon
uv sync                                  # first run downloads Python 3.12 + build123d (~1-2 min)
uv run pytest                            # 7 tests; the slicer test runs only if your slicer is installed
uv run python -m fitcoupon.build         # out/plates/fit_coupon_1.3mf (+ STEP, plates.csv)
```

Open `out/plates/fit_coupon_1.3mf` in Bambu Studio (File → Open Project): gray plate, orange marks, one color
change. Print it, try the peg in each hole, and use the clearance that slides. Not on a Bambu A1? Set up your
printer first (next section); it takes a minute.

## Your setup

Nothing to edit in the code: describe your printer with environment variables, or copy
[`cadkit.toml.example`](cadkit.toml.example) to `cadkit.toml` (ignored by git, so `git pull` never conflicts) or to
`~/.config/cadkit/cadkit.toml`. With nothing set you get the setup this was built on: a Bambu A1, a 4-color AMS lite,
Bambu Studio.

| Setting | Env var | Default |
|---|---|---|
| Bed (mm) | `CADKIT_BED` (square) or `CADKIT_BED_X` + `CADKIT_BED_Y` | 256 × 256 |
| Layer, first layer, nozzle (mm) | `CADKIT_LAYER`, `CADKIT_FIRST_LAYER`, `CADKIT_NOZZLE` | 0.2, 0.2, 0.4 |
| Colors the printer can use | `CADKIT_COLORS` (1 = no AMS: everything on filament 1) | 4 |
| Color changes per plate before a warning | `CADKIT_COLOR_CHANGES` | 1 |
| Slicer | `CADKIT_SLICER` (`bambu`, or `none` to skip slicer checks), `CADKIT_SLICER_PATH` | `bambu` |
| Where new projects go | `CADKIT_PROJECTS` (any folder, in git or not) | `examples/` |

```bash
cd cadkit && uv run python -m cadkit.settings      # what's in effect, and where each value came from
```

Packing, print checks and plate files follow these settings, and the fit coupon and candle adapter adapt their
heights to your layer height. A part bigger than your bed fails its test with the numbers, so Claude splits it.
The railroad and the sunflower were sized for the A1 at 0.2 mm; on other setups their tests name what to change. When a design wants more colors or swaps than you set, the build warns and Claude
offers alternatives: split the colors by height, print a detail separately and glue it, or drop a color.

## Start your own project

- **With Claude:** open this repo (or any folder, with the skill installed below) in Claude Code and describe the
  thing: *"use print-cad to design a wall bracket for my router, 2 screws, prints flat"*. Expect sketches and 2–3
  options first, then a spec, then parts built test-first with renders, then plates checked through the slicer and
  an independent review before you print.
- **By hand:** `cd cadkit && uv run python -m cadkit.new my-bracket` copies the fit-coupon template into your
  projects folder (`CADKIT_PROJECTS`; default `examples/`), renames the package and points it at this cadkit. Keep
  the layout: `params.py`, `parts.py` (or `parts/`), `build.py`, `tests/`, pictures in `docs/images/`.

### Installing the skill for all your projects

Project skills in `.claude/skills/` load automatically inside this repo. To use `print-cad` everywhere:

```bash
mkdir -p ~/.claude/skills
ln -s "$PWD/.claude/skills/print-cad" ~/.claude/skills/print-cad
```

## The approach in one screen

- **Every dimension lives in one `params.py`,** including the printer and which AMS slot holds which color. A
  design change is a one-line edit, and tests derive their expectations from params.
- **Parts print flat with no supports.** They're 2D profiles extruded to a thickness, made in print orientation and
  placed into the assembly by a separate transform. Nothing starts over air: not a bridge over a hole, not an upper
  color past the edge of the lower one.
- **Snap or slot to locate, glue only for strength.** Tabs, bow-tie keys, half-laps and latches, with clearances
  tuned by a printed fit-test coupon.
- **The assembly clash test is the backbone.** It includes the environment (walls, ceiling, doors, even walls you
  don't draw), moving envelopes and the hardware, and it has a variant that must fail.
- **Multi-color without the waiting.** Color changes are a budget you set (default one per plate): two-color parts
  change once, at a layer boundary, and never share a plate with single-color parts. Over budget, the build says so
  and suggests alternatives. The 3MF has one object with a filament per part; the STEP has one painted solid.
- **The slicer is the last test.** Plates round-trip through the slicer's CLI and get sliced: same filaments, same
  geometry, the planned color changes. Three real bugs got past green unit tests and were caught only this way.
- **Look before you trust.** Preview renders and a 3D viewer, because some mistakes pass every test.

The full story of each rule is in [lessons.md](.claude/skills/print-cad/references/lessons.md).

## Viewing

- **OCP CAD Viewer** shows models without any STEP translation: `uv run python -m ocp_viewer --port 3939`, open
  http://127.0.0.1:3939/viewer **first**, then send (`cadkit.view.show(shape)` or an example's `build show`).
- **Onshape:** Create → Import with the plain `.step` (not zipped). Colors and part names come through.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `uv sync` fails on Python / OCP wheels | Run `uv python install 3.12`, then `uv sync` again. Don't change the 3.12 pin. |
| Bambu Studio: "The 3mf is not from Bambu Lab", everything one color | That file came from an old build or another tool. Rebuild; cadkit plates are Bambu projects. Open with File → Open Project. |
| Bambu Studio shows copies of one part where there should be different ones | An old build with per-file mesh ids. Rebuild. |
| The viewer page is blank, or still shows the old model | Open the page **before** sending; reload it and send again. Split very large models. |
| Onshape rejects the file | Upload the plain `.step`, not a zip. Large rooms take minutes to translate. |
| Tests are slow | Use `-n <cores>` (pytest-xdist) and `-m "not slow"` while iterating; run the full suite before committing. |
| `UnicodeEncodeError` in tests | The process has an ASCII locale. cadkit writes UTF-8 explicitly; set `LANG=en_US.UTF-8` for older code. |

## Safety

Things you print can hold things up, including over people (the railroad hangs on walls and a ceiling). Screw into
studs where you can, use anchors rated well beyond the load where you can't, and check your own fixings. No
warranty (see LICENSE).

## License

[MIT](LICENSE). Use it, change it, print it, share it; keep the copyright notice.
