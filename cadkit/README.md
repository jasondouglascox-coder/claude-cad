# cadkit

The reusable half of claude-cad: print-ready output and checks for [build123d](https://github.com/gumyr/build123d)
parts. Every module was pulled out of a real project after it had earned its place there.

## Use it in a project

```toml
# pyproject.toml
dependencies = ["build123d==0.13.0", "cadkit"]          # "cadkit[viewer]" adds OCP CAD Viewer

[tool.uv.sources]
cadkit = { path = "../../cadkit", editable = true }     # path from your project to this folder
```

```python
from cadkit import A1, Printer
from cadkit.checks import printable_problems, open_edges, off_layer_z, unsupported
from cadkit.export import write_plates
from cadkit.plates import Plate, pack

assert printable_problems(part, A1) == [] and open_edges(part) == 0 and off_layer_z(part, A1) == []
beds = pack([("bracket", part), ("deck", two_color_deck)], A1)        # two-color parts on their own plates
write_plates([Plate(f"p{n + 1}", 1, items) for n, items in enumerate(beds)], out / "plates",
             out / "plates.csv", filament_for=lambda label: 2 if label.endswith("_wood") else 1)
```

A two-color part is a `Compound` of two colored, labeled bodies, lower color first. `filament_for` maps each
body's label to a filament (AMS slot).

## Modules

| Module | What it does |
|---|---|
| `printer` | `Printer(bed=256, margin=5, layer=0.2, nozzle=0.4)`, `A1` |
| `shapes` | `rect`, `poly` (counter-clockwise, so it extrudes up), `grow` (clearance), `bowtie`, `dovetail` |
| `checks` | `printable_problems`, `open_edges`, `off_layer_z`, `unsupported`, `downward_faces` |
| `clash` | `find_clashes([(name, shape)])`: pairs sharing volume, touching doesn't count |
| `paint` | `painted(lower, color, upper, color)` → one solid with face colors; `export_step` writes them; `display_parts` splits a placed copy for viewers |
| `plates` | `pack(items, printer)` (MaxRects, 3 mm gap, both rotations), `Plate`, `is_two_color`, `zeroed` |
| `bambu3mf` | `write(path, objects, settings=...)`: Bambu Studio project 3MF; `read_filaments`, `read_meshes`, `object_sizes` |
| `bambu` | `find()`, `roundtrip(src)`, `slice_report(src)`: Bambu Studio's CLI as a test oracle (set `BAMBU_STUDIO` if it isn't in the default place) |
| `export` | `write_plates`, `write_svg` (hidden-line preview), view constants `TOP`, `FRONT`, `ISO` |
| `view` | `show(shape)`, `colored(items, color_for)`: OCP CAD Viewer (`CADKIT_VIEWER_HOST` for another machine) |

Why each exists, and the traps behind them: `../.claude/skills/print-cad/references/printing.md` and
`lessons.md`.

## Tests

```bash
uv sync && uv run pytest -n 4     # ~10 s; the Bambu Studio test runs only if it's installed
```
