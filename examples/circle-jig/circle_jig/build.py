"""uv run python -m circle_jig.build [--out out]: STEP for CAD, a plate for your slicer (opens orange in Bambu
Studio), and shaded previews in out/render (iso.png, top.png) to copy to docs/images/ after a visible change."""
import argparse
import sys
from pathlib import Path

from build123d import Color, export_step

from cadkit.export import write_plates
from cadkit.plates import Plate
from cadkit.render import render
from circle_jig.params import P
from circle_jig.parts import jig, on_bed

ORANGE = Color(0.95, 0.55, 0.15)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="circle_jig.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    j = jig(P)
    step = out / "step" / "circle_jig.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    export_step(j, step)
    write_plates([Plate("circle_jig_1", 1, [("circle_jig", on_bed(P))])], out / "plates", out / "plates.csv",
                 lambda name: P.filament)
    render([(j, ORANGE)], out / "render" / "iso.png", view=(0.4, -1, 0.9), px=900, crop=True)
    render([(j, ORANGE)], out / "render" / "top.png", view=(0, 0, 1), px=900, crop=True)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
