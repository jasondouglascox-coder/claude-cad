"""uv run python -m loaf_spacer.build [--out out]: STEP for CAD, a Bambu Studio plate that opens black, and a
shaded preview in out/render/front.png (looking down the pan's length)."""
import argparse
import sys
from pathlib import Path

from build123d import Color, export_step

from cadkit.export import write_plates
from cadkit.plates import Plate, pack
from cadkit.render import render
from loaf_spacer.params import P
from loaf_spacer.parts import spacer


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="loaf_spacer.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    s = spacer(P)
    step = out / "step" / "loaf_spacer.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    export_step(s, step)
    beds = pack([("loaf_spacer", s)], P.printer)
    write_plates([Plate(f"loaf_spacer_{n + 1}", 1, items) for n, items in enumerate(beds)], out / "plates",
                 out / "plates.csv", lambda name: P.filament_black)
    gray = Color(0.18, 0.18, 0.18)  # black filament, lifted enough to see the shading
    render([(s, gray)], out / "render" / "front.png", view=(0, 0, 1), px=600)
    render([(s, gray)], out / "render" / "iso.png", view=(0.4, -0.6, 1), px=600)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
