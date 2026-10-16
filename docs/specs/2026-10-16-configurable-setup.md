# Your printer, your slicer, your folder: settings without editing cadkit

## Why

claude-cad was built on one setup: a Bambu A1 (256 × 256 mm), four AMS colors, Bambu Studio, projects in
`examples/`. Others have other printers (a Prusa MK4 is 250 × 210, an Ender 220 × 220), other slicers (PrusaSlicer,
Cura, OrcaSlicer), one color, or want their projects outside this repo. They should clone, describe their setup,
and start designing: **without editing cadkit, and with `git pull` never conflicting with their settings.**

## Goals

- Every machine-specific value comes from one place: environment variables, or an untracked `cadkit.toml`.
- With nothing set, everything behaves exactly as before (A1, Bambu Studio, 4 colors, `examples/`). Same plates,
  same tests.
- Slicers sit behind one small interface. Bambu Studio is the built-in one. Someone with PrusaSlicer or Cura can add
  theirs in one file and send a PR, and a shared contract test tells them when it works.
- Color changes are a budget, not a law. A one-color printer gets one-color plates. When a design needs more colors
  or changes than the setup allows, the build says so and names the options.
- Every example ships pictures in its README (`docs/images/`), made by the project's own `build render`.

## Non-goals

- Implementing PrusaSlicer or Cura. We define the slot; contributors fill it.
- Re-sizing the examples' designs to every bed. A part that doesn't fit your bed fails its test with the
  footprint and the bed size, which is the honest answer. Packing does adapt to your bed.
- Moving per-project choices (which AMS slot holds which color in the railroad) out of each project's params.

## Anti-goals

- Anything that changes Jason's plates or makes his tests fail with nothing set.
- A settings file that's tracked by git (pulls would conflict).

## Settings (`cadkit.settings`)

Read in this order, later wins: built-in defaults → the config file → environment variables.

| Setting | Env var | Default | Meaning |
|---|---|---|---|
| `printer.bed_x`, `printer.bed_y` | `CADKIT_BED_X`, `CADKIT_BED_Y` (`CADKIT_BED` sets both) | 256, 256 | bed, mm |
| `printer.margin` | `CADKIT_MARGIN` | 5 | kept clear across the bed |
| `printer.layer` | `CADKIT_LAYER` | 0.2 | layer height |
| `printer.first_layer` | `CADKIT_FIRST_LAYER` | (= layer) | first layer height |
| `printer.nozzle` | `CADKIT_NOZZLE` | 0.4 | nozzle diameter |
| `colors.count` | `CADKIT_COLORS` | 4 | filaments the printer can use in one print (AMS lite: 4; no AMS: 1) |
| `colors.changes` | `CADKIT_COLOR_CHANGES` | 1 | color changes per plate before the build warns |
| `slicer.name` | `CADKIT_SLICER` | `bambu` | a registered slicer, or `none` |
| `slicer.path` | `CADKIT_SLICER_PATH` | (the slicer's usual place; `BAMBU_STUDIO` still works) | the slicer's executable |
| `slicer.settings` | `CADKIT_SLICER_SETTINGS` | (the slicer's built-in template) | the slicer's project-settings template |
| `projects.dir` | `CADKIT_PROJECTS` | `<repo>/examples` | where `cadkit.new` puts new projects |

Config file: `$CADKIT_CONFIG` if set, else `cadkit.toml` at the repo root (gitignored), else
`~/.config/cadkit/cadkit.toml`. `cadkit.toml.example` (tracked) lists every key, commented out.
`uv run python -m cadkit.settings` prints the effective values and where each came from.

`cadkit.Printer()` takes its defaults from these settings; `cadkit.A1` stays the literal A1. `Printer` gains
`bed_y` (None = square, so `Printer(bed=256)` still means 256 × 256), and checks and packing use both sides.

## Slicers (`cadkit.slicers`)

A `Slicer` has: `name`, `find()` (executable or None), `available()`, `write_project(path, objects, settings)`,
`read_filaments(path)`, `roundtrip(src, dst)`, `slice_report(src, dst)` → `{"grams": {filament: g}, "layers":
[(filaments, first, last)]}`. The base class writes a plain-enough 3MF that any slicer loads (the Bambu project
format); a slicer overrides `write_project` to write its own project format so plates open colored.

Registered: `bambu` (wraps the existing `cadkit.bambu` and `cadkit.bambu3mf`, unchanged) and `none` (writes the
same 3MF, can't round-trip or slice, so slicer tests skip). `cadkit.slicers.active()` returns the configured one.
`cadkit/tests/test_slicers.py` runs the same contract against every registered slicer, skipping what isn't
installed. `CONTRIBUTING.md` says how to add one.

Example tests use `active()` and skip when it isn't available, instead of calling Bambu directly.

## Colors

- `cadkit.plates.color_changes(items, key=)` counts a plate's swaps layer by layer, by filament (key) or by body
  color: k filaments in a layer cost k - 1 swaps, plus one when the layer can't start on the last one's filament
  (the order is optimized). Stacked colors cost one per seam; colors side by side cost one every layer. It's an
  estimate from bounding boxes; the slicer test is the truth.
- `cadkit.checks.color_problems(items, colors=, changes=)` lists what's over the setup's limits, each message with
  the options: split the color by height, print the detail as a separate part and glue it, drop a color, or
  allow more changes for this plate.
- `write_plates` with `colors.count == 1` puts every body on filament 1 (multi-color parts keep their shape and print
  in one color), and packing stops keeping multi-color parts apart. With more colors than the printer has, it stops
  with which plate, which filaments, and those options.
- A plate whose design accepts more swaps says so: `Plate(..., color_changes=n)`, recorded in its spec (the
  sunflower's beaded front quarter and the 10" one-piece). Every other plate is held to the settings budget.

## Projects folder

`uv run --project cadkit python -m cadkit.new <name>` copies the fit-coupon template into `projects.dir/<name>`:
renames the package, points the cadkit path dependency at this checkout, and leaves README, `docs/specs/` and
`docs/images/` ready. The skill creates new projects there.

## Images

Every example has `build render` writing `out/render/*.png` (cadkit.render) and copies in `docs/images/` shown at
the top of its README. A cadkit test checks each example's README shows at least one image that exists. fit-coupon
gets its render; the template carries it to new projects.

## Left to the builder

Exact env var parsing, message wording, how `cadkit.new` renames, which views each example renders.

## Amendments
