"""uv run python -m candle.build [--out out]: STEP for CAD, a Bambu Studio plate that opens black, and shaded
previews in out/render (iso.png, section.png: cut in half through the candle hole)."""
import argparse
import sys
from pathlib import Path

from build123d import Align, Box, Color, Pos, export_step

from cadkit.export import write_plates
from cadkit.plates import Plate, pack
from cadkit.render import render
from candle.params import P
from candle.parts import adapter


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="candle.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    a = adapter(P)
    step = out / "step" / "candle_adapter.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    export_step(a, step)
    beds = pack([("candle_adapter", a)], P.printer)
    write_plates([Plate(f"candle_adapter_{n + 1}", 1, items) for n, items in enumerate(beds)], out / "plates",
                 out / "plates.csv", lambda name: P.filament_black)
    gray = Color(0.18, 0.18, 0.18)  # black filament, lifted enough to see the shading
    half = a & Pos(0, P.base_d / 2, 0) * Box(4 * P.base_d, 4 * P.base_d, 4 * P.height, align=(Align.MIN,) * 3)
    render([(a, gray)], out / "render" / "iso.png", view=(0.5, -1, 0.6), px=600)
    render([(half, gray)], out / "render" / "section.png", view=(0, -1, 0.15), px=600)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
