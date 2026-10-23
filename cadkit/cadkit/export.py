"""Write what the CAD tool and the slicer need: STEP (with painted face colors), SVG previews, and build plates
as STEP + the slicer's project file (cadkit.slicers; Bambu Studio 3MF by default) + a quantity sheet."""
import csv
import warnings
from pathlib import Path
from typing import Callable

from build123d import Compound, ExportSVG, LineType, Shape

from cadkit import paint
from cadkit.mesh import Mesh
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


def _overlaps(s: Shape, rect: tuple) -> bool:
    """Does the part reach into the (x0, y0, x1, y1) column? Bounding boxes first, then the real shape (a round part's
    box reaches a corner its body doesn't)."""
    from build123d import Align, Box, Pos
    x0, y0, x1, y1 = rect
    bb = s.bounding_box()
    if not (bb.min.X < x1 and bb.max.X > x0 and bb.min.Y < y1 and bb.max.Y > y0):
        return False
    col = Pos(x0, y0, bb.min.Z - 1) * Box(x1 - x0, y1 - y0, bb.size.Z + 2, align=(Align.MIN,) * 3)
    parts = bodies(s) if isinstance(s, Compound) and s.children else [s]
    return any(b.bounding_box().min.X < x1 and (b & col).volume > 1e-6 for b in parts)


def write_plates(plates: list[Plate], folder: Path, csv_path: Path, filament_for: Callable[[str], int],
                 preview_dir: Path | None = None, settings: Path | None = None, slicer=None,
                 colors: int | None = None, color_changes: int | None = None, combined: str | None = None) -> None:
    """Each plate as STEP (painted) + the slicer's project file + an optional SVG, and csv_path listing what to print
    and how many. slicer: default the one in your settings (cadkit.slicers.active()). settings: the slicer's project
    settings (for Bambu, bambu3mf.write_settings for your filaments); default its template.
    filament_for(body label) -> filament number; multi-color parts are one object with a part per color
    body, so the upper color can't drop onto the bed.

    colors (default: settings) is how many filaments the printer can use: with 1, every body goes on filament 1;
    a plate needing a filament past it stops with the options. A plate with more color swaps than color_changes
    (default: settings) still gets written, with a warning saying what to do instead; pass the number a design
    accepts.

    combined: also write every plate into one project, folder/<combined> + the slicer's suffix (a tab per plate,
    "(print n)" in the name of plates printed more than once): the file to share, e.g. on MakerWorld."""
    from cadkit import slicers
    from cadkit.checks import ADVICE
    from cadkit.settings import settings as cfg
    slicer = slicer or slicers.active()
    colors = cfg().colors if colors is None else colors
    budget = cfg().color_changes if color_changes is None else color_changes
    if colors == 1:
        filament_for = lambda name: 1  # a one-color printer: everything on filament 1
    folder.mkdir(parents=True, exist_ok=True)
    rows, everything = [], []
    for pl in plates:
        children = []
        for name, s in pl.items:
            s.label = name
            children.append(s)
        if any(isinstance(s, Mesh) for s in children):  # no B-rep, so no STEP: the plate's geometry as STL
            whole = [s if isinstance(s, Mesh) else Mesh.from_shape(s) for s in children]
            (whole[0] if len(whole) == 1 else Mesh.union(whole)).write_stl(folder / f"{pl.name}.stl")
            comp = None
        else:
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
        tower = slicer.tower_keepout(settings, pad=0.0) if swaps else None  # the tower itself, not the packer's pad
        if tower is not None:
            x0, y0, x1, y1 = tower
            hit = [s.label for s in children if _overlaps(s, tower)]
            if hit:
                warnings.warn(f"{pl.name}: {', '.join(hit)} sits where the prime tower prints (x {x0:.0f}-{x1:.0f}, "
                              f"y {y0:.0f}-{y1:.0f} mm), so the slicer won't slice it. Place parts with "
                              f"cadkit.plates.pack, or move the tower in the slicer.", stacklevel=2)
        slicer.write_project(folder / f"{pl.name}{slicer.project_suffix}", objects, settings)
        everything.append((pl.name + (f" (print {pl.qty})" if pl.qty > 1 else ""), objects))
        if preview_dir is not None and comp is not None:
            write_svg(comp, preview_dir / f"plate_{pl.name}.svg", TOP)
        counts = {}
        for name, _ in pl.items:
            base = name.split("#")[0]
            counts[base] = counts.get(base, 0) + 1
        rows.append([pl.name, pl.qty, "; ".join(f"{n} x{c}" for n, c in counts.items())])
    if combined:
        slicer.write_combined(folder / f"{combined}{slicer.project_suffix}", everything, settings)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:  # utf-8: test workers may run with ASCII locale
        w = csv.writer(f)
        w.writerow(["plate", "quantity", "contents"])
        w.writerows(rows)
