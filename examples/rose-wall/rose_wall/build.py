"""uv run python -m rose_wall.build [all|plates|step|render] [--out out]

plates: out/plates/rose.3mf (a Bambu project: red PLA, tree supports with a PETG interface) + .step, out/plates.csv
step:   out/rose.step for CAD
render: out/render/*.png shaded previews (copy to docs/images/ after a visible change)
"""
import argparse
import sys
from pathlib import Path

from build123d import export_step

from cadkit.render import ISO, TOP, render
from rose_wall import flower
from rose_wall.params import P


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rose_wall.build")
    ap.add_argument("what", nargs="?", default="all", choices=["all", "plates", "step", "render"])
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.what in ("all", "plates"):
        flower.write(P, out)
    if a.what in ("all", "step"):
        export_step(flower.make(P), str(out / "rose.step"))
    if a.what in ("all", "render"):
        rose = flower.make(P)
        for name, view in (("front", TOP), ("iso", ISO), ("side", (-0.3, -1.0, 0.9))):
            render([(rose, rose.color)], out / "render" / f"{name}.png", view=view)
    print(f"wrote {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
