"""uv run python -m peony_wall.build [all|plates|render] [--out out]

plates: out/plates/peony.3mf (soft pink, no supports) and stamens.3mf (the yellow insert), each with an .stl (a
        mesh: no STEP), and out/plates.csv
render: out/render/*.png shaded previews, the insert in place (copy to docs/images/ after a visible change)
"""
import argparse
import sys
from pathlib import Path

import cadkit.render as cr
from cadkit.render import ISO, TOP, render
from peony_wall import flower
from peony_wall.params import P

LIGHT = (-0.25, 0.35, 1.0)  # lit from the front, a little above-left: how it hangs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="peony_wall.build")
    ap.add_argument("what", nargs="?", default="all", choices=["all", "plates", "render"])
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.what in ("all", "plates"):
        flower.write(P, out)
    if a.what in ("all", "render"):
        cr.LIGHT = LIGHT
        items = [(flower.body(P), P.color(P.slot_flower)), (flower.insert_placed(P), P.color(P.slot_insert))]
        for name, view in (("front", TOP), ("iso", ISO), ("side", (-0.3, -1.0, 0.9))):
            render(items, out / "render" / f"{name}.png", view=view, tol=0.05)
        render([(flower.insert(P), P.color(P.slot_insert))], out / "render" / "stamens.png", view=(0.4, -1, 0.7),
               px=600, crop=True)
    print(f"wrote {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
