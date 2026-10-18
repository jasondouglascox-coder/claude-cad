"""uv run python -m sharpie_colorizer.build [fit] [--out out]

fit: the fit-test plate only (print it first), STEP per piece, and out/render/fit_test.png."""
import argparse
import sys
from pathlib import Path

from build123d import Color, Pos, export_step

from cadkit.export import write_plates
from cadkit.plates import Plate, pack
from cadkit.render import render
from sharpie_colorizer.params import P
from sharpie_colorizer.parts.fittest import fit_items

GRAY = Color(0.18, 0.18, 0.18)  # black filament, lifted enough to see the shading


def _steps(items, out: Path) -> None:
    (out / "step").mkdir(parents=True, exist_ok=True)
    for name, part in items:
        export_step(part, out / "step" / f"{name}.step")


def _plates(name: str, items, out: Path) -> list[Plate]:
    return [Plate(f"{name}_{n + 1}", 1, bed) for n, bed in enumerate(pack(items, P.printer))]


def fit(out: Path) -> list[Plate]:
    items = fit_items(P)
    _steps(items, out)
    plates = _plates("fit_test", items, out)
    x, shown = 0.0, []
    for _, part in items:  # side by side for the picture
        bb = part.bounding_box()
        shown.append((Pos(x - bb.min.X, -bb.min.Y, 0) * part, GRAY))
        x += bb.size.X + 6
    render(shown, out / "render" / "fit_test.png", view=(0.4, -1, 0.9), px=900)
    return plates


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sharpie_colorizer.build")
    ap.add_argument("what", nargs="?", default="fit", choices=["fit"])
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    out = Path(a.out)
    plates = fit(out)
    write_plates(plates, out / "plates", out / "plates.csv", lambda name: P.filament_black)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
