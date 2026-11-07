"""uv run python -m speaker_shelf.build [--out out]: STEP for CAD, the fit-coupon plate for your slicer (opens black
in Bambu Studio), and a shaded preview in out/render/fit_coupon.png."""
import argparse
import sys
from pathlib import Path

from build123d import Color, export_step

from cadkit.export import write_plates
from cadkit.plates import Plate, pack
from cadkit.render import render
from speaker_shelf.parts import gap_gauge, rail_fork
from speaker_shelf.params import P

SHOWN = Color(0.18, 0.18, 0.18)  # black filament, lifted enough to see the shading


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="speaker_shelf.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    fork, gauge = rail_fork(P), gap_gauge(P)
    (out / "step").mkdir(parents=True, exist_ok=True)
    for part in (fork, gauge):
        export_step(part, out / "step" / f"{part.label}.step")
    beds = pack([("rail_fork", fork), ("gap_gauge", gauge)], P.printer)
    assert len(beds) == 1, "the coupon fits one plate"
    write_plates([Plate("fit_coupon", 1, beds[0])], out / "plates", out / "plates.csv", lambda name: P.filament_black)
    render([(s, SHOWN) for _, s in beds[0]],
           out / "render" / "fit_coupon.png", view=(0.4, -1, 1.2), px=800, crop=True)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
