"""Write the cut files and previews.

out/cat_sheet_in.dxf, out/cat_sheet_mm.dxf: the full 24 x 24 mat (same sheet; open whichever comes in with the test
square measuring 1"). out/cats/<pose>.dxf: one cat each, in inches, to place and repeat in Studio.
out/render/poses.png, sheet.png: previews."""
import shutil
from pathlib import Path

from . import cats, dxf, render, sheet
from .params import P

OUT = Path(__file__).resolve().parent.parent / "out"
DOCS = OUT.parent / "docs" / "images"


def main():
    (OUT / "cats").mkdir(parents=True, exist_ok=True)
    (OUT / "render").mkdir(exist_ok=True)
    shapes = sheet.layout()
    for units in ("in", "mm"):
        dxf.write(OUT / f"cat_sheet_{units}.dxf", [s for _, s in shapes], units)
    each = {n: cats.cat(n) for n in cats.POSES}
    for n, s in each.items():
        dxf.write(OUT / "cats" / f"{n}.dxf", [s])
    render.poses(OUT / "render" / "poses.png", each)
    render.sheet(OUT / "render" / "sheet.png", [s for _, s in shapes], P.mat)
    DOCS.mkdir(parents=True, exist_ok=True)
    for f in ("poses.png", "sheet.png"):
        shutil.copy(OUT / "render" / f, DOCS / f)
    n = sum(name != "test_square" for name, _ in shapes)
    print(f"{n} cats on the {P.mat[0]:g} x {P.mat[1]:g} in mat, {len(each)} poses -> {OUT}")


if __name__ == "__main__":
    main()
