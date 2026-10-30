"""uv run python -m circle_jig.build [--out out]: STEP for CAD (assembled), two plates for your slicer (open orange
in Bambu Studio), and shaded previews in out/render (iso.png assembled, on_bed.png both plates) to copy to
docs/images/ after a visible change."""
import argparse
import sys
from pathlib import Path

from build123d import Align, Box, Color, Compound, Pos, export_step

from cadkit.export import write_plates
from cadkit.render import render
from circle_jig.params import P
from circle_jig.parts import extension, hub, key_in_place, plates

ORANGE, BED = Color(0.95, 0.55, 0.15), Color(0.25, 0.25, 0.27)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="circle_jig.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    pieces = [hub(P), extension(P), key_in_place(P)]
    step = out / "step" / "circle_jig.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    export_step(Compound(children=pieces, label="circle_jig"), step)
    beds = plates(P)
    write_plates(beds, out / "plates", out / "plates.csv", lambda name: P.filament)
    render([(x, ORANGE) for x in pieces], out / "render" / "iso.png", view=(0.4, -1, 0.9), px=1000, crop=True)
    bed_y = P.printer.bed_y or P.printer.bed
    shown = []
    for i, plate in enumerate(beds):  # side by side, each on its bed
        dx = i * (P.printer.bed + 20)
        shown.append((Pos(dx, 0, -1) * Box(P.printer.bed, bed_y, 1, align=(Align.MIN,) * 3), BED))
        shown += [(Pos(dx, 0, 0) * x, ORANGE) for _, x in plate.items]
    render(shown, out / "render" / "on_bed.png", view=(0, 0, 1), px=1000, crop=True)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
