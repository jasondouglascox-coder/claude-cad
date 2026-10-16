"""uv run python -m fitcoupon.build [--out out]: STEP for CAD, plates for your slicer (they open colored in Bambu
Studio), and a shaded preview in out/render/iso.png (copy it to docs/images/ after a visible change)."""
import argparse
import sys
from pathlib import Path

from build123d import Pos

from cadkit import paint
from cadkit.export import write_plates
from cadkit.plates import Plate, pack
from cadkit.render import render
from fitcoupon.parts import coupon, peg
from fitcoupon.params import P

FILAMENT = {"coupon_base": 1, "coupon_marks": 2}  # your AMS slots


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fitcoupon.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    c = coupon(P)
    step = out / "step" / "coupon.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    paint.export_step(paint.painted(c.children[0], c.children[0].color, c.children[1], c.children[1].color), step)
    beds = pack([("coupon", c), ("peg", peg(P))], P.printer)
    write_plates([Plate(f"fit_coupon_{n + 1}", 1, items) for n, items in enumerate(beds)], out / "plates",
                 out / "plates.csv", lambda name: FILAMENT.get(name, 1))
    render([(b, b.color) for b in c.children] + [(Pos(-P.peg_d - 4, 0, 0) * peg(P), c.children[0].color)],
           out / "render" / "iso.png", view=(0.5, -1, 0.9), px=600, crop=True)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
