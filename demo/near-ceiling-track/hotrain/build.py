"""Command line: export STEP files (and optional STL / SVG previews) for the run in layout.BAYS.

    uv run python -m hotrain.build all          # parts + assembly + fit test
    uv run python -m hotrain.build parts        # one STEP per distinct part + out/manifest.csv
    uv run python -m hotrain.build assembly     # out/step/run_assembly.step + demo_two_bays.step
    uv run python -m hotrain.build fit-test     # out/step/fit_test.step
    uv run python -m hotrain.build plates       # out/plates/*.step + *.3mf, packed build plates + out/plates.csv
    uv run python -m hotrain.build corners      # out/corners/*.step, corner assemblies, out/corners_layout.csv
    uv run python -m hotrain.build room         # out/step/office.step: the whole office, walls and track (colored)
    uv run python -m hotrain.build show [room|run|inside|bridge|fit-test] [--run-style deck_truss] [--corner-style bowstring]   # OCP CAD Viewer
    uv run python -m hotrain.build glb          # out/glb/*.glb per section
    uv run python -m hotrain.build web          # out/web: phone/web 3D viewer page + glTF JSON models + manifest
    uv run python -m hotrain.build check        # interference check, exit 1 on any clash
    uv run python -m hotrain.build starter --run-style deck_truss   # out/starter: one 16" bay + fit-test coupon
Options: --out DIR (default out), --mesh (also STL), --preview (also SVG line drawings)
"""
import argparse
import csv
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

from build123d import Compound, ExportSVG, LineType, Mesher, Shape, export_step, export_stl

from hotrain import assembly, paint, plates
from hotrain import layout as L
from hotrain.params import INCH, P, Params
from hotrain.parts import arch_half, bracket, cross_frame, end_pier, fit_test, handrail, keystone, tie_ladder

TOP = ((0, 0, 1), (0, 1, 0))  # (view direction toward the eye, up) for flat parts
FROM_ROOM = ((0, 1, 0), (0, 0, 1))  # assembly seen from the room
CORNER_VIEW = ((-0.6, -1.0, 0.7), (0, 0, 1))


def write_svg(shape: Shape, path: Path, view: tuple) -> None:
    direction, up = view
    bb = shape.bounding_box()
    c = bb.center()
    dist = 10 * max(bb.size.X, bb.size.Y, bb.size.Z)
    origin = (c.X + direction[0] * dist, c.Y + direction[1] * dist, c.Z + direction[2] * dist)
    visible, hidden = shape.project_to_viewport(origin, viewport_up=up, look_at=(c.X, c.Y, c.Z))
    span = max(bb.size.X, bb.size.Y, bb.size.Z)
    exp = ExportSVG(scale=800 / span)
    exp.add_layer("visible")
    exp.add_layer("hidden", line_color=(0.63, 0.63, 0.63), line_type=LineType.ISO_DOT)
    exp.add_shape(visible, layer="visible")
    exp.add_shape(hidden, layer="hidden")
    path.parent.mkdir(parents=True, exist_ok=True)
    exp.write(str(path))


def export(shape: Shape, out: Path, name: str, mesh: bool, preview: bool, view: tuple = TOP,
           subdir: str = "step") -> Path:
    step = out / subdir / f"{name}.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(shape, Compound) or "assembly" not in name and name != "demo_two_bays":
        shape.label = name
    paint.export_step(shape, step)  # build123d's export, plus painted face colors
    if mesh:
        stl = out / "stl" / f"{name}.stl"
        stl.parent.mkdir(parents=True, exist_ok=True)
        export_stl(shape, str(stl))
    if preview:
        write_svg(shape, out / "preview" / f"{name}.svg", view)
    return step


def part_list(p: Params, bays: list[float], ends: tuple = L.RUN_ENDS) -> list[tuple[str, Shape, int, str]]:
    """(name, part, quantity, note) for every distinct printable part in the run."""
    rows = []
    for b, n in sorted(Counter(round(b, 3) for b in bays).items()):
        tag = f"{b:.1f}mm"
        rows.append((f"arch_half_{tag}", arch_half.make(p, b), 4 * n, f"{n} bay(s) of {b:.1f} mm; 2 panels x 2 halves"))
        for k, u in enumerate(L.post_us(p, b)):
            d = L.cf_depth(p, b, u)
            rows.append((f"cross_frame_{tag}_{k}", cross_frame.make(p, d), 2 * n, f"post {k + 1} from each pier"))
    rows.append(("keystone", keystone.make(p), 2 * len(bays), "one per panel per bay"))
    corners = sum(e == L.CORNER for e in ends)
    rows.append(("bracket", bracket.make(p), len(bays) + 1 - corners, "one per pier (corner anchors replace end brackets)"))
    if corners < 2:
        rows.append(("end_pier", end_pier.make(p), 2 * (2 - corners), "two per free run end"))
    for k, seg in enumerate(L.segments(p, bays, ends)):
        rows.append((f"ladder_{k:02d}", tie_ladder.make(p, bays, seg, ends), 1,
                     f"x {seg.x_start:.1f} to {seg.x_end:.1f} mm"))
    for k, pc in enumerate(L.handrail_pieces(p, bays, ends)):
        rows.append((f"handrail_{k:02d}", handrail.make(p, pc), 1,
                     f"x {pc.x_start:.1f} to {pc.x_end:.1f} mm, {len(pc.posts)} posts"))
    return rows


def cmd_parts(p: Params, bays: list[float], out: Path, mesh: bool, preview: bool) -> None:
    rows = part_list(p, bays)
    for name, shape, _, _ in rows:
        export(shape, out, name, mesh, preview)
    with open(out / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "quantity", "note"])
        for name, _, qty, note in rows:
            w.writerow([f"step/{name}.step", qty, note])


def cmd_assembly(p: Params, bays: list[float], out: Path, mesh: bool, preview: bool) -> None:
    export(assembly.make(p, bays), out, "run_assembly", mesh, preview, FROM_ROOM)
    # Two default bays sharing one bracket, to show how units join (independent of BAYS).
    export(assembly.make(p, [p.bay_len, p.bay_len]), out, "demo_two_bays", mesh, preview, FROM_ROOM)


def add_multipart(mesher: Mesher, bodies: list, name: str | None = None) -> None:
    """Add bodies as ONE 3MF object with one part per body (Bambu Studio: one object, assign a filament per
    part), instead of separate objects that the slicer would each drop onto the bed."""
    n0 = len(mesher.meshes)
    for b in bodies:
        mesher.add_shape(b)
    meshes = mesher.meshes[n0:]
    ids = {m.GetResourceID() for m in meshes}
    items = mesher.model.GetBuildItems()
    doomed = []
    while items.MoveNext():
        it = items.GetCurrent()
        if it.GetObjectResourceID() in ids:
            doomed.append(it)
    for it in doomed:
        mesher.model.RemoveBuildItem(it)
    group = mesher.model.AddComponentsObject()
    if name:
        group.SetName(name)
    for m in meshes:
        group.AddComponent(m, mesher.wrapper.GetIdentityTransform())
    mesher.model.AddBuildItem(group, mesher.wrapper.GetIdentityTransform())


def write_plates(pls: list, d: Path, csv_path: Path, preview_dir: Path | None = None) -> None:
    """Each plate as STEP (painted) + 3MF (one object per part, per color), plus a quantity sheet."""
    d.mkdir(parents=True, exist_ok=True)
    rows = []
    for pl in pls:
        children = []
        for name, s in pl.items:
            s.label = name
            children.append(s)
        comp = Compound(children=children, label=pl.name)
        paint.export_step(comp, d / f"{pl.name}.step")
        mesher = Mesher()
        for s in children:
            if plates.is_two_color(s):
                add_multipart(mesher, s.children, s.label)
            else:
                for body in (s.children if isinstance(s, Compound) and s.children else [s]):
                    mesher.add_shape(body)
        mesher.write(str(d / f"{pl.name}.3mf"))
        if preview_dir is not None:
            write_svg(comp, preview_dir / f"plate_{pl.name}.svg", TOP)
        counts = {}
        for name, _ in pl.items:
            base = name.split("#")[0]
            counts[base] = counts.get(base, 0) + 1
        rows.append([pl.name, pl.qty, "; ".join(f"{n} x{c}" for n, c in counts.items())])
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["plate", "quantity", "contents"])
        w.writerows(rows)


def cmd_plates(p: Params, bays: list[float], out: Path, preview: bool) -> None:
    write_plates(plates.plates(p, bays) + plates.corner_plates(p), out / "plates", out / "plates.csv",
                 out / "preview" if preview else None)


def cmd_starter(p: Params, out: Path, bay_in: float = 16.0) -> Path:
    """One free-standing straight bay (two brackets, both end piers) plus the fit-test coupon: out/starter/."""
    from hotrain.plates import Plate
    d = out / "starter"
    pls = plates.all_in_one(p, [bay_in * INCH]) + [Plate("fit_test", 1, [("fit_test", fit_test.make(p))])]
    write_plates(pls, d, d / "plates.csv")
    return d


def cmd_corners(p: Params, out: Path, mesh: bool, preview: bool) -> None:
    from hotrain import corner_assembly, corner_layout
    from hotrain.parts import rod_jig
    seen = set()
    for corner in (corner_layout.inside_corner(), corner_layout.bridge_corner()):
        for name, shape in plates.corner_kit(p, corner):
            if name not in seen:
                seen.add(name)
                export(shape, out, name, mesh, preview, subdir="corners")
        export(corner_assembly.make(p, corner), out, f"{corner.name}_corner_assembly", mesh, preview,
               CORNER_VIEW, subdir="corners")
    export(rod_jig.make(p), out, "rod_jig", mesh, preview, subdir="corners")
    with open(out / "corners_layout.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["corner", "item", "measure", "mm", "inches"])
        for corner in (corner_layout.inside_corner(), corner_layout.bridge_corner()):
            for item, how, mm in corner_layout.layout_sheet(p, corner):
                w.writerow([corner.name, item, how, f"{mm:.1f}", f"{mm / 25.4:.2f}"])


def cmd_fit_test(p: Params, out: Path, mesh: bool, preview: bool) -> None:
    export(fit_test.make(p), out, "fit_test", mesh, preview)


def params_from_args(a: argparse.Namespace) -> Params:
    """P with any style overrides from the command line."""
    p = P
    if getattr(a, "run_style", None):
        p = replace(p, run_style=a.run_style)
    if getattr(a, "corner_style", None):
        p = replace(p, corner_style=a.corner_style)
    return p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hotrain.build", description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["all", "parts", "assembly", "fit-test", "plates", "corners", "room", "show", "glb", "web",
                                        "check", "starter"])
    ap.add_argument("target", nargs="?", default="room", help="for show: room | run | inside | bridge | fit-test")
    ap.add_argument("--out", default="out")
    ap.add_argument("--mesh", action="store_true")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--run-style", choices=["arch", "deck_truss"], help="straight-run style (default: params)")
    ap.add_argument("--corner-style", choices=["pony", "bowstring"], help="corner side frames (default: params)")
    a = ap.parse_args(argv)
    out, p, bays = Path(a.out), params_from_args(a), L.BAYS
    L.validate_bays(p, bays)
    out.mkdir(parents=True, exist_ok=True)
    if a.command == "check":
        clashes = assembly.find_clashes(assembly.placed_parts(p, bays))
        for na, nb, v in clashes:
            print(f"CLASH {na} x {nb}: {v} mm^3")
        print("no clashes" if not clashes else f"{len(clashes)} clash(es)")
        return 1 if clashes else 0
    if a.command in ("all", "parts"):
        cmd_parts(p, bays, out, a.mesh, a.preview)
    if a.command in ("all", "assembly"):
        cmd_assembly(p, bays, out, a.mesh, a.preview)
    if a.command in ("all", "fit-test"):
        cmd_fit_test(p, out, a.mesh, a.preview)
    if a.command == "web":
        from hotrain import room
        web = room.build_web(p, out)
        print(f"wrote {web}/office-viewer.html + models/ (publish the page with every models/*.json attached)")
        return 0
    if a.command == "glb":
        from hotrain import room
        for path in room.export_glbs(p, out / "glb"):
            print(f"{path}  {path.stat().st_size / 1e6:.1f} MB")
        return 0
    if a.command == "starter":
        d = cmd_starter(p, out)
        print(f"wrote {d}/ (plates.csv lists what to print and how many)")
        return 0
    if a.command == "show":
        from hotrain import view
        view.show(p, a.target)
        print(f"sent {a.target} to http://{view.host()}:{view.PORT}/viewer")
        return 0
    if a.command == "room":
        from hotrain import room
        export(room.make(p), out, "office", a.mesh, False)  # top label "office"; sections keep their names
    if a.command in ("all", "corners"):
        cmd_corners(p, out, a.mesh, a.preview)
    if a.command in ("all", "plates"):
        cmd_plates(p, bays, out, a.preview)
    print(f"wrote {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
