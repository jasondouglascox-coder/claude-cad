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
cd examples/sunflower-wall && uv sync && uv run pytest -p no:xdist -m "not slow"   # ~50 min, ~20 GB peak
```

Heavy suites use a lot of memory per worker, because each worker builds its own whole-model fixtures. Lower `-n`
if your machine starts swapping.

Bambu Studio is optional. Tests that drive its CLI skip when it isn't installed.

### Rules

These are the same rules the project holds itself to ([CLAUDE.md](CLAUDE.md) and the
[print-cad skill](.claude/skills/print-cad/SKILL.md) have the detail):

- **Test first.** Write the failing test, then the code. Tests derive their expectations from `params.py`, with
  no magic numbers.
- **Every dimension lives in `params.py`.**
- **Keep the print rules green** (`cadkit.checks`): flat, one solid, no supports, watertight, Z levels on layer
  multiples, the upper color never over air, at most one color change per plate.
- **Generic code goes in `cadkit/`** with a test in `cadkit/tests/`. Project code stays in its project.
- **If plates or 3MF output change**, run them through Bambu Studio's CLI (`cadkit.bambu`). CI can't run Bambu
  Studio, so say in the PR whether you did.
- **If something visible changes**, render it and attach the picture to the PR.
- **If a design decision changes**, add an amendment to that project's `docs/specs/*.md`. Real-world measurements
  go in `docs/measurements.md`, with where each one was measured from.
- **Never commit `out/`.** It's generated.

### New example projects

Copy `examples/fit-coupon`, rename the package, and keep its layout (`params.py`, `parts.py`, `build.py`,
`tests/`). Add the project to the matrix in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) so CI tests it.

### CI

Every PR runs each project's `-m "not slow"` suite on Linux. The sunflower's 10" one-piece tests
(`examples/sunflower-wall/tests/test_small.py`) need more memory than a CI runner has. If you touch the sunflower
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
