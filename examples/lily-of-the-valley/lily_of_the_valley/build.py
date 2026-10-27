"""uv run python -m lily_of_the_valley.build [all|plates|render] [--out out]

plates: out/plates/lily_of_the_valley.3mf (a Bambu project: white bells, green sprig, 20 swaps, no supports)
        + lily_of_the_valley.stl (a mesh: no STEP), out/plates.csv
render: out/render/*.png shaded previews in the planned colours (plate.png: both sprigs as they print) (copy to docs/images/ after a visible change)
"""
import argparse
import sys
from pathlib import Path

import numpy as np

import cadkit.render as cr
from cadkit.mesh import Mesh
from cadkit.render import TOP, render
from lily_of_the_valley import flower
from lily_of_the_valley.params import P

LIGHT = (-0.25, 0.35, 1.0)  # lit from the front, a little above-left: how it hangs


def hung(m: Mesh) -> Mesh:
    """On the wall: the print's z (out of the wall) toward you (-Y), its y up (+Z)."""
    v = m.verts
    return Mesh(np.stack([v[:, 0], -v[:, 2], v[:, 1]], 1), m.tris, m.label, m.color)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lily_of_the_valley.build")
    ap.add_argument("what", nargs="?", default="all", choices=["all", "plates", "render"])
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.what in ("all", "plates"):
        flower.write(P, out)
    if a.what in ("all", "render"):
        items = [(b, b.color) for b, _ in flower.coloured(P)]
        cr.LIGHT = LIGHT
        render(items, out / "render" / "front.png", view=TOP, px=1400, tol=0.05, crop=True)
        cr.LIGHT = (LIGHT[0], -LIGHT[2], LIGHT[1])  # the same light, turned with the sprig onto the wall
        render([(hung(b), c) for b, c in items], out / "render" / "side.png", view=(0.75, -1.0, 0.25), px=1400,
               tol=0.05, crop=True)
        render([(hung(b), c) for b, c in items], out / "render" / "below.png", view=(0.3, -1.0, -0.6), px=1400,
               tol=0.05, crop=True)
        cr.LIGHT = LIGHT
        render([(m, m.color) for _, parts in flower.plate(P) for _, m, _ in parts], out / "render" / "plate.png",
               view=TOP, px=1400, tol=0.05, crop=True)
    print(f"wrote {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
