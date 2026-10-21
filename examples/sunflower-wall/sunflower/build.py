"""uv run python -m sunflower.build [all|plates|step|render|makerworld] [--out out]

plates:     out/plates/sunflower_10in.3mf (a Bambu project that opens colored, your AMS filaments) + .step,
            out/plates.csv
step:       out/sunflower_10in.step, the whole flower painted in its colors, for Onshape
render:     out/render/*.png shaded previews
makerworld: out/makerworld/sunflower_10in.3mf: the print profile, sliced (G-code and thumbnail), ready to upload to
            MakerWorld. The upload is yours.
"""
import argparse
import sys
from pathlib import Path

from cadkit import paint
from cadkit.render import ISO, TOP, render
from sunflower import flower

NAME = "sunflower_10in"


def write_step(out: Path) -> Path:
    path = out / f"{NAME}.step"
    out.mkdir(parents=True, exist_ok=True)
    paint.export_step(flower.make(flower.params()), str(path))
    return path


def write_renders(out: Path) -> list[Path]:
    piece = flower.make(flower.params())
    items = [(b, b.color) for b in piece.children]
    paths = []
    for name, view in (("front", TOP), ("iso", ISO), ("side", (-0.45, -1.0, 0.35))):
        path = out / "render" / f"{name}.png"
        render(items, path, view=view)
        paths.append(path)
    return paths


def write_makerworld(out: Path) -> Path:
    """The print profile as one sliced project in out/makerworld/."""
    from cadkit import slicers
    s, d = slicers.active(), out / "makerworld"
    work = d / "work"
    flower.write(flower.params(), work, combined=NAME)
    reports = s.slice_all(work / "plates" / f"{NAME}{s.project_suffix}", d / f"{NAME}{s.project_suffix}")
    print(f"{NAME}: {len(reports)} plate sliced")
    return d


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sunflower.build")
    ap.add_argument("what", nargs="?", default="all", choices=["all", "plates", "step", "render", "makerworld"])
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.what == "makerworld":
        print(f"wrote {write_makerworld(out)}/: the sliced project, ready to upload")
        return 0
    if a.what in ("all", "plates"):
        flower.write(flower.params(), out)
    if a.what in ("all", "step"):
        write_step(out)
    if a.what in ("all", "render"):
        write_renders(out)
    print(f"wrote {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
