"""uv run python -m sunflower.build [all|plates|step|render] [--out out]

plates: out/plates/*.3mf (Bambu projects that open colored, your AMS filaments) + .step, out/plates.csv
step:   out/step/*.step, one per part, plus sunflower_assembly.step (the whole flower) for Onshape
render: out/render/*.png shaded previews of the assembled flower
"""
import argparse
import sys
from pathlib import Path

from build123d import Color, Compound, export_step

from cadkit import bambu3mf
from cadkit.export import write_plates
from cadkit.render import ISO, TOP, render
from sunflower import assembly, layout
from sunflower.params import P, Params
from sunflower.parts import center, pin, quarter
from sunflower.plates import filament_for, plans


def _hex(c: str) -> Color:
    return Color(*(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)))


def colors(p: Params) -> dict:
    fil = {k + 1: _hex(c) for k, (_, c) in enumerate(p.filaments)}
    f = filament_for(p)
    return {name: fil[f(name)] for name in ("back_quarter", "front_quarter", "pin", "center_black", "center_brown")}


def write_plate_files(p: Params, out: Path) -> None:
    settings = bambu3mf.write_settings(out / "bambu_project_settings.config", list(p.filaments))
    write_plates(plans(p), out / "plates", out / "plates.csv", filament_for(p), settings=settings)


def write_steps(p: Params, out: Path) -> None:
    col = colors(p)
    (out / "step").mkdir(parents=True, exist_ok=True)
    for layer in ("back", "front"):
        part = quarter.make(p, layer)
        part.color = col[part.label]
        export_step(part, str(out / "step" / f"{part.label}.step"))
    snap = pin.make(p)
    snap.color = col["pin"]
    export_step(snap, str(out / "step" / "pin.step"))
    head = center.make(p)
    for b in head.children:
        b.color = col[b.label]
    export_step(head, str(out / "step" / "seed_head.step"))
    export_step(assembled(p), str(out / "step" / "sunflower_assembly.step"))


def assembled(p: Params) -> Compound:
    """The whole flower as hung (wall at z = 0), an assembly tree for CAD: placed copies of one shape per part
    type, so the file stays small and Onshape lists 4 back_quarter, 4 front_quarter, 8 pin and the seed_head."""
    col = colors(p)
    kids = []
    for layer in ("back", "front"):
        base = quarter.make(p, layer)
        base.color = col[base.label]
        for q in range(4):
            placed = quarter.place(p, layer, q) * base
            placed.label, placed.color = base.label, base.color
            kids.append(placed)
    bodies = []
    for b in center.make(p).children:
        moved = center.place(p) * b
        moved.label, moved.color = b.label, col[b.label]
        bodies.append(moved)
    kids.append(Compound(children=bodies, label="seed_head"))
    snap = pin.make(p)
    snap.color = col["pin"]
    for a in layout.pin_angles(p):
        placed = pin.place(p, a) * snap
        placed.label, placed.color = "pin", snap.color
        kids.append(placed)
    return Compound(children=kids, label="sunflower")


def write_renders(p: Params, out: Path) -> list[Path]:
    col = colors(p)
    items = [(s, col[name.split("_")[0] + "_quarter" if name[:4] in ("back", "fron") else
                  "pin" if name.startswith("pin") else name]) for name, s in assembly.placed_parts(p)]
    paths = []
    for name, view in (("front", TOP), ("iso", ISO), ("side", (0.0, -1.0, 0.12))):
        path = out / "render" / f"{name}.png"
        render(items, path, view=view)
        paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sunflower.build")
    ap.add_argument("what", nargs="?", default="all", choices=["all", "plates", "step", "render"])
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.what in ("all", "plates"):
        write_plate_files(P, out)
    if a.what in ("all", "step"):
        write_steps(P, out)
    if a.what in ("all", "render"):
        write_renders(P, out)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
