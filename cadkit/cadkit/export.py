"""Write what the CAD tool and the slicer need: STEP (with painted face colors), SVG previews, and build plates
as STEP + the slicer's project file (cadkit.slicers; Bambu Studio 3MF by default) + a quantity sheet."""
import csv
import warnings
from pathlib import Path
from typing import Callable

from build123d import Compound, ExportSVG, LineType, Shape

from cadkit import paint
from cadkit.plates import Plate, bodies, is_multi_color
from cadkit.plates import color_changes as count_changes

TOP = ((0, 0, 1), (0, 1, 0))  # (view direction toward the eye, up): flat parts from above
FRONT = ((0, -1, 0), (0, 0, 1))
ISO = ((-0.6, -1.0, 0.7), (0, 0, 1))


def write_svg(shape: Shape, path: Path, view: tuple = TOP) -> None:
    """Hidden-line drawing (hidden lines dotted). Turn it into a PNG with `rsvg-convert -b white -w 1400 in.svg -o
    out.png` and look at it: some mistakes pass every test. Whole-room drawings are slow; render subsets."""
    direction, up = view
    bb = shape.bounding_box()
    c = bb.center()
    dist = 10 * max(bb.size.X, bb.size.Y, bb.size.Z)
    origin = (c.X + direction[0] * dist, c.Y + direction[1] * dist, c.Z + direction[2] * dist)
    visible, hidden = shape.project_to_viewport(origin, viewport_up=up, look_at=(c.X, c.Y, c.Z))
    span = max(bb.size.X, bb.size.Y, bb.size.Z)
    exp = ExportSVG(scale=800 / span)
    exp.add_layer("visible")
    exp.add_layer("hidden", line_color=(0.63, 0.63, 0.63), line_type=LineType.ISO_DOT)
    exp.add_shape(visible, layer="visible")
    exp.add_shape(hidden, layer="hidden")
    path.parent.mkdir(parents=True, exist_ok=True)
    exp.write(str(path))


def write_plates(plates: list[Plate], folder: Path, csv_path: Path, filament_for: Callable[[str], int],
                 preview_dir: Path | None = None, settings: Path | None = None, slicer=None,
                 colors: int | None = None, color_changes: int | None = None) -> None:
    """Each plate as STEP (painted) + the slicer's project file + an optional SVG, and csv_path listing what to print
    and how many. slicer: default the one in your settings (cadkit.slicers.active()). settings: the slicer's project
    settings (for Bambu, bambu3mf.write_settings for your filaments); default its template.
    filament_for(body label) -> filament number; multi-color parts are one object with a part per color
    body, so the upper color can't drop onto the bed.

    colors (default: settings) is how many filaments the printer can use: with 1, every body goes on filament 1;
    a plate needing a filament past it stops with the options. A plate with more color swaps than color_changes
    (default: settings) still gets written, with a warning saying what to do instead; pass the number a design
    accepts."""
    from cadkit import slicers
    from cadkit.checks import ADVICE
    from cadkit.settings import settings as cfg
    slicer = slicer or slicers.active()
    colors = cfg().colors if colors is None else colors
    budget = cfg().color_changes if color_changes is None else color_changes
    if colors == 1:
        filament_for = lambda name: 1  # a one-color printer: everything on filament 1
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for pl in plates:
        children = []
        for name, s in pl.items:
            s.label = name
            children.append(s)
        comp = Compound(children=children, label=pl.name)
        paint.export_step(comp, folder / f"{pl.name}.step")
        objects = []
        for s in children:
            if is_multi_color(s):
                objects.append((s.label, [(b.label, b, filament_for(b.label)) for b in bodies(s)]))
            else:
                for body in (bodies(s) if isinstance(s, Compound) and s.children else [s]):
                    objects.append((s.label, [(s.label, body, filament_for(s.label))]))
        over = sorted({f for _, parts in objects for _, _, f in parts if f > colors})
        if over:
            raise ValueError(f"plate {pl.name}: filament {', '.join(map(str, over))}, but the printer has {colors} "
                             f"colors (CADKIT_COLORS). Set CADKIT_COLORS=1 to print everything in one color, or "
                             f"change the project's filament numbers. " + ADVICE)
        swaps = count_changes(pl.items, key=lambda name, body: filament_for(name)) if colors > 1 else 0
        allowed = budget if pl.color_changes is None else pl.color_changes
        if swaps > allowed:
            warnings.warn(f"{pl.name}: {swaps} color changes, over the budget of {allowed}. " + ADVICE, stacklevel=2)
        slicer.write_project(folder / f"{pl.name}{slicer.project_suffix}", objects, settings)
        if preview_dir is not None:
            write_svg(comp, preview_dir / f"plate_{pl.name}.svg", TOP)
        counts = {}
        for name, _ in pl.items:
            base = name.split("#")[0]
            counts[base] = counts.get(base, 0) + 1
        rows.append([pl.name, pl.qty, "; ".join(f"{n} x{c}" for n, c in counts.items())])
    with open(csv_path, "w", newline="", encoding="utf-8") as f:  # utf-8: test workers may run with ASCII locale
        w = csv.writer(f)
        w.writerow(["plate", "quantity", "contents"])
        w.writerows(rows)
