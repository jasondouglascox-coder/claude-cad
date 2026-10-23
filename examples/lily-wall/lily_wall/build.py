"""uv run python -m lily_wall.build [all|plates|render] [--out out]

plates: out/plates/lily.3mf (a Bambu project: white and purple PLA, the long fade, tree supports with a PETG
        interface) + lily.stl (a mesh: no STEP), out/plates.csv
render: out/render/*.png shaded previews in the planned colours (copy to docs/images/ after a visible change)
"""
import argparse
import sys
from pathlib import Path

import cadkit.render as cr
from cadkit.render import ISO, TOP, render
from lily_wall import flower
from lily_wall.params import P

LIGHT = (-0.25, 0.35, 1.0)  # lit from the front, a little above-left: how it hangs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lily_wall.build")
    ap.add_argument("what", nargs="?", default="all", choices=["all", "plates", "render"])
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.what in ("all", "plates"):
        flower.write(P, out)
    if a.what in ("all", "render"):
        cr.LIGHT = LIGHT
        items = [(b, b.color) for b, _ in flower.coloured(P)]
        for name, view in (("front", TOP), ("iso", ISO), ("side", (-0.3, -1.0, 0.7))):
            render(items, out / "render" / f"{name}.png", view=view, tol=0.05)
        render(items, out / "render" / "fade.png", view=TOP, px=2600, tol=0.03)  # close enough to see the layers
    print(f"wrote {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
