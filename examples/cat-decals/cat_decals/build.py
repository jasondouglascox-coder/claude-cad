"""Write the cut files and previews.

out/cat_sheet_in.dxf: one of each cat and a 1" test square on the 24 x 24 mat, in inches.
out/render/poses.png, sheet.png: previews."""
import shutil
from pathlib import Path

from . import cats, dxf, render, sheet
from .params import P

OUT = Path(__file__).resolve().parent.parent / "out"
DOCS = OUT.parent / "docs" / "images"


def main():
    (OUT / "render").mkdir(parents=True, exist_ok=True)
    shapes = sheet.layout()
    dxf.write(OUT / "cat_sheet_in.dxf", [s for _, s in shapes])
    each = {n: cats.cat(n) for n in cats.POSES}
    render.poses(OUT / "render" / "poses.png", each)
    render.sheet(OUT / "render" / "sheet.png", [s for _, s in shapes], P.mat)
    DOCS.mkdir(parents=True, exist_ok=True)
    for f in ("poses.png", "sheet.png"):
        shutil.copy(OUT / "render" / f, DOCS / f)
    print(f"{len(each)} cats on the {P.mat[0]:g} x {P.mat[1]:g} in mat -> {OUT / 'cat_sheet_in.dxf'}")


if __name__ == "__main__":
    main()
