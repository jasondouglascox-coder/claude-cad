# Contributing to claude-cad

Bug reports, print reports, new examples, cadkit helpers and doc fixes are all welcome. Anyone can open an issue
or a pull request. The maintainer ([@jasondouglascox-coder](https://github.com/jasondouglascox-coder)) reviews
and merges everything into `main`.

By taking part you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Issues

- **Something broke** (a crash, a failing test, a bad 3MF or STEP): use the *Bug report* form. Include the command,
  the full output, and your OS, `uv --version` and Bambu Studio version.
- **A part printed or fit badly**: use the *Print problem* form. Photos and caliper measurements help most. Say
  which printer, filament, nozzle and layer height you used.
- **An idea** (a cadkit helper, a new check, a new example): use *Feature request*. For a big change, open the
  issue before you write the code.
- **A security problem in the code**: don't open an issue. See [SECURITY.md](SECURITY.md).
- **A design that could fail under load** (a bracket, an anchor, anything over people): open an issue now. Safety
  problems in a design are not secret.

## Pull requests

You can't push branches to this repo directly. Fork it, branch from `main`, and open a PR back to `main`.

```bash
git clone https://github.com/<you>/claude-cad.git
cd claude-cad
git checkout -b fix-dovetail-clearance
# ...change, test, commit...
git push -u origin fix-dovetail-clearance
```

Keep each PR to one change. Maintainers can push to your branch to finish small things, so leave *Allow edits by
maintainers* on.

### Setup

You need [uv](https://docs.astral.sh/uv/). Every project is its own uv project, run from its own folder:

```bash
cd cadkit && uv sync && uv run pytest -n 4
cd examples/fit-coupon && uv sync && uv run pytest
cd examples/candle-adapter && uv sync && uv run pytest
cd examples/near-ceiling-track && uv sync && uv run pytest -n 4 -m "not slow"   # full suite ~25 min
cd examples/sunflower-wall && uv sync && uv run pytest -n 3 --dist loadfile -m "not slow"   # ~12 min, ~12 GB a worker
```

Heavy suites use a lot of memory per worker, because each worker builds its own whole-model fixtures. Lower `-n`
if your machine starts swapping.

Bambu Studio is optional. Tests that drive a slicer's CLI skip when it isn't installed. The suites are meant to
pass on any setup: run them with your own settings too (`CADKIT_*` variables or `cadkit.toml`).

### Rules

These are the same rules the project holds itself to ([CLAUDE.md](CLAUDE.md) and the
[print-cad skill](.claude/skills/print-cad/SKILL.md) have the detail):

- **Test first.** Write the failing test, then the code. Tests derive their expectations from `params.py`, with
  no magic numbers.
- **Every dimension lives in `params.py`.**
- **Keep the print rules green** (`cadkit.checks`): flat, one solid, no supports, watertight, Z levels on layer
  multiples, the upper color never over air. Color changes stay within the budget (default one per plate) unless
  the plate's design accepts more (`Plate(..., color_changes=n)`, recorded in the spec).
- **Generic code goes in `cadkit/`** with a test in `cadkit/tests/`. Project code stays in its project.
- **If plates or 3MF output change**, run them through the slicer's CLI (`cadkit.slicers.active()`; Bambu Studio by
  default). CI can't run a slicer, so say in the PR whether you did.
- **If something visible changes**, render it, refresh the project's `docs/images/`, and attach the picture to the
  PR.
- **If a design decision changes**, add an amendment to that project's `docs/specs/*.md`. Real-world measurements
  go in `docs/measurements.md`, with where each one was measured from.
- **Never commit `out/`.** It's generated.

### New example projects

Start one with `cd cadkit && uv run python -m cadkit.new <name> --dir ../examples` (it copies `examples/fit-coupon`,
renames the package and wires up cadkit), and keep its layout (`params.py`, `parts.py`, `build.py`, `tests/`).
Show renders at the top of its README from `docs/images/`; `cadkit/tests/test_examples.py` checks they exist. Add
the project to the matrix in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) so CI tests it.

### Your setup is not a code change

Bed size, layer height, colors, slicer and projects folder come from `cadkit.settings`: environment variables or a
`cadkit.toml` that git ignores (see [cadkit.toml.example](cadkit.toml.example)). If something about your printer
needs a code edit, that's a bug: open an issue, or add the setting (one row in `settings.KEYS`, a field on
`Settings`, a line in `cadkit.toml.example`; the tests check the three agree).

### Adding a slicer

Bambu Studio is the one cadkit ships with. Adding PrusaSlicer, OrcaSlicer, Cura or another takes one file:

1. Create `cadkit/cadkit/slicers/<name>.py`:

   ```python
   from pathlib import Path
   from cadkit.slicers import Slicer, Unavailable, register

   @register
   class PrusaSlicer(Slicer):
       name, label = "prusa", "PrusaSlicer"

       def find(self) -> Path | None:
           ...  # settings().slicer_path when settings().slicer == name, else where it usually installs

       def write_project(self, path, objects, settings=None) -> Path:
           ...  # optional: your slicer's project format, so plates open with each part on its filament

       def read_filaments(self, path):
           ...  # needed if you override write_project: read back [(object, filament, {part: filament})]

       def roundtrip(self, src, dst=None) -> Path:
           ...  # load src in the slicer and save it back (its CLI)

       def slice_report(self, src, dst=None) -> dict:
           ...  # slice plate 1: {"grams": {filament: g}, "layers": [(filaments, first layer, last layer)]}

       def tower_keepout(self, settings=None):
           ...  # optional: (x0, y0, x1, y1) where your prime/wipe tower prints; multi-color plates leave it free
   ```

2. Import it at the bottom of `cadkit/cadkit/slicers/__init__.py`, next to `bambu`.
3. Run `uv run pytest tests/test_slicers.py`. The contract runs against every registered slicer: the file tests
   always run, and the round-trip and slicing tests run when your slicer is installed.
4. Select it with `CADKIT_SLICER=<name>` and run an example's tests (`examples/fit-coupon` is quick).

What to implement depends on what the slicer can do:

- **It has a command line that slices** (PrusaSlicer, OrcaSlicer): implement everything. Slicing in the tests is
  what caught five real bugs that unit tests missed.
- **It has no slicing CLI** (Cura): implement `write_project`/`read_filaments` if its project format can carry a
  filament per part, and leave `find()` returning None. `available()` is then False, `roundtrip` and
  `slice_report` raise `Unavailable`, and the slicer tests skip instead of failing.
- **Neither:** you don't need a class. `CADKIT_SLICER=none` writes standard 3MF plates any slicer can open (set
  the colors by hand) and skips the slicer checks.

Every filament number is 1-based, as slicers show them. A part whose filament is `bambu3mf.BLOCKER` is a support blocker (a volume the slicer must put no support in, from `Plate(blockers=...)`): write it as your slicer's blocker if it has one, and leave it out of `read_filaments`. The `settings` argument to `write_project` is whatever
the project passes (the examples pass a Bambu project-settings file); ignore it if it means nothing to your slicer.

### Adding a printer

Usually nothing to add: set the bed, margin, layer and nozzle. If your printer needs a slicer project template
(Bambu's printer model lives there), save one from the slicer and point `slicer.settings` at it.


### CI

Every PR runs each project's `-m "not slow"` suite on Linux. The sunflower's whole-flower tests
(`examples/sunflower-wall/tests/test_flower.py`) need more memory than a CI runner has. If you touch the sunflower
or cadkit, run them locally and say so in the PR. A PR merges only once CI is green. Workflows on a
first-time contributor's PR wait for maintainer approval before they run.

### Commit messages

Start with the project, then say what changed in a plain sentence:

```
Candle adapter: thin flared foot (0.8 mm edge) sloping up into the collar
cadkit: downward_faces ignores faces resting on the bed
```

## Using Claude Code

The `print-cad` skill and `CLAUDE.md` load automatically when you open this repo in Claude Code. Contributions
written with AI help are welcome. You're still responsible for them: read the diff, run the tests, and look at the
renders before you open the PR.

## License

Contributions are licensed under the [MIT License](LICENSE), the same as the rest of the project.
