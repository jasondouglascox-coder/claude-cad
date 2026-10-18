"""uv run python -m sharpie_colorizer.build [all | fit] [--out out]

all (default): both plates (fit_test_1 first, then colorizer_1), STEP per part plus the assembly on the bar, and
renders in out/render: assembly.png, section.png (cut through the channel and the back marker), fit_test.png.
fit: the fit-test plate only."""
import argparse
import sys
from pathlib import Path

from build123d import Align, Box, Color, Compound, Pos, export_step

from cadkit.export import write_plates
from cadkit.render import render
from sharpie_colorizer.assembly import _block_frame, filament, placed_parts
from sharpie_colorizer.joints import marker_solid
from sharpie_colorizer.params import P
from sharpie_colorizer.parts import block
from sharpie_colorizer.parts.fittest import fit_items
from sharpie_colorizer.plates import colorizer_items, plates

BLACK = Color(0.18, 0.18, 0.18)  # black filament, lifted enough to see the shading
COLORS = {"bar": Color(0.72, 0.73, 0.75), "inlet_tube": Color(0.95, 0.95, 0.93),
          "outlet_tube": Color(0.95, 0.95, 0.93), "filament": Color(1, 1, 1)}
RED = Color(0.75, 0.1, 0.12)


def _steps(items, out: Path) -> None:
    (out / "step").mkdir(parents=True, exist_ok=True)
    for name, part in items:
        export_step(part, out / "step" / f"{name}.step")


def _side_by_side(items) -> list:
    x, shown = 0.0, []
    for _, part in items:
        bb = part.bounding_box()
        shown.append((Pos(x - bb.min.X, -bb.min.Y, 0) * part, BLACK))
        x += bb.size.X + 6
    return shown


def _whole_marker(i: int):
    """A marker with its grip, for pictures."""
    return _block_frame(P) * block.marker_frame(P, i) * marker_solid(P, "long", with_grip=True)


def fit(out: Path) -> None:
    items = fit_items(P)
    _steps(items, out)
    render(_side_by_side(items), out / "render" / "fit_test.png", view=(0.4, -1, 0.9), px=900)


def parts(out: Path) -> None:
    _steps(colorizer_items(P), out)
    placed = placed_parts(P)
    shown = [(s, COLORS.get(n, BLACK)) for n, s in placed if not n.startswith("marker")]
    shown += [(_whole_marker(i), RED) for i in range(len(P.azimuths_deg))]
    for n, s in placed:
        s.label = n
    export_step(Compound(children=[s for _, s in placed], label="assembly"), out / "step" / "assembly.step")
    render(shown, out / "render" / "assembly.png", view=(1, 0.8, 0.55), px=900)
    keep = Pos(0, -25, 0) * Box(60, 75, 75, align=(Align.MIN,) * 3)  # x >= 0 (the back marker's plane), around the block
    cut = [(s & keep, c) for s, c in [(placed[2][1], BLACK), (_whole_marker(0), RED), (filament(P), COLORS["filament"])]]
    render(cut, out / "render" / "section.png", view=(-1, 0, 0.12), px=900)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sharpie_colorizer.build")
    ap.add_argument("what", nargs="?", default="all", choices=["all", "fit"])
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    out = Path(a.out)
    fit(out)
    todo = plates(P)
    if a.what == "all":
        parts(out)
    else:
        todo = [pl for pl in todo if pl.name.startswith("fit_test")]
    write_plates(todo, out / "plates", out / "plates.csv", lambda name: P.filament_black)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
