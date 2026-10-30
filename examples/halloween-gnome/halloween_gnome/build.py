"""uv run python -m halloween_gnome.build [all|plates|render] [--out out]

plates: out/plates/halloween_gnome.3mf, a Bambu project with a plate per print (body, hat, nose), each opening in
        its colours; each print's .stl (meshes: no STEP); out/plates.csv
render: out/render/*.png shaded previews in the planned colours (copy to docs/images/ after a visible change)
"""
import argparse
import sys
from pathlib import Path

import numpy as np

import cadkit.render as cr
from cadkit import bambu3mf, slicers
from cadkit.mesh import Mesh
from cadkit.render import render
from halloween_gnome import gnome
from halloween_gnome.params import P, Params

FRONT, ISO, BACK = (0.0, -1.0, 0.15), (0.6, -1.0, 0.45), (-0.6, 1.0, 0.45)


def prints(p: Params) -> list[tuple[str, list[Mesh], int]]:
    """(name, bodies lowest colour first, colour changes) for each print, centred on the bed."""
    out = []
    for name, bodies in (("body", gnome.body(p)), ("hat", gnome.hat(p)), ("nose", [gnome.nose(p)])):
        lo = np.min([b.verts.min(0) for b in bodies], axis=0)
        hi = np.max([b.verts.max(0) for b in bodies], axis=0)
        mid = (p.printer.bed / 2 - (lo[0] + hi[0]) / 2, (p.printer.bed_y or p.printer.bed) / 2 - (lo[1] + hi[1]) / 2, 0)
        out.append((name, [b.translate(mid) for b in bodies], len(bodies) - 1))
    return out


def slot(p: Params, label: str) -> int:
    return {"black": p.slot_black, "orange": p.slot_orange, "white": p.slot_white, "brim": p.slot_black,
            "band": p.slot_orange, "crown": p.slot_black, "nose": p.slot_pink}[label.split("_")[-1]]


def write_plates(p: Params, out: Path) -> Path:
    """One project, a plate per print. Returns its path."""
    folder = out / "plates"
    folder.mkdir(parents=True, exist_ok=True)
    settings = bambu3mf.write_settings(out / "bambu_project_settings.config", list(p.filaments))
    s = slicers.active()
    everything, rows = [], []
    for name, bodies, swaps in prints(p):
        objects = [(f"gnome_{name}", [(b.label, b, slot(p, b.label)) for b in bodies])]
        s.write_project(folder / f"gnome_{name}{s.project_suffix}", objects, settings)
        Mesh.union(bodies).write_stl(folder / f"gnome_{name}.stl")
        everything.append((f"gnome_{name}", objects))
        rows.append(f"gnome_{name},1,{name} ({swaps} colour changes)")
    path = folder / f"halloween_gnome{s.project_suffix}"
    s.write_combined(path, everything, settings)
    (out / "plates.csv").write_text("plate,quantity,contents\n" + "\n".join(rows) + "\n")
    return path


def write_renders(p: Params, out: Path) -> None:
    cr.LIGHT = (-0.5, -1.0, 0.9)  # from the front, above-left
    items = [(m, m.color) for m in gnome.assembled(p)]
    for name, view in (("front", FRONT), ("iso", ISO), ("back", BACK)):
        render(items, out / "render" / f"{name}.png", view=view, px=1000, tol=0.05, crop=True)
    parts = []
    for k, (_, bodies, _) in enumerate(prints(p)):
        parts += [(b.translate(((k - 1) * 48, 0, 0)), b.color) for b in bodies]
    render(parts, out / "render" / "prints.png", view=ISO, px=1200, tol=0.05, crop=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="halloween_gnome.build")
    ap.add_argument("what", nargs="?", default="all", choices=["all", "plates", "render"])
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.what in ("all", "plates"):
        write_plates(P, out)
    if a.what in ("all", "render"):
        write_renders(P, out)
    print(f"wrote {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
