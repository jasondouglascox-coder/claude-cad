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
    uv run python -m hotrain.build render --run-style deck_truss   # out/render/*.png shaded previews
    uv run python -m hotrain.build check        # interference check, exit 1 on any clash
    uv run python -m hotrain.build wire-test    # out/wire_test: stainless wire rail curve test plates (0.08 mm layers)
    uv run python -m hotrain.build makerworld   # out/makerworld: one sliced project per print profile, to upload
    uv run python -m hotrain.build latch-test   # out/latch_test: three latch hook lengths + two pier stubs
    uv run python -m hotrain.build sections --run-style deck_truss   # out/sections: the room a bay at a time
Options: --out DIR (default out), --mesh (also STL), --preview (also SVG line drawings)
"""
import argparse
import csv
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

from build123d import Compound, Shape, export_stl

from cadkit import export as cad_export
from cadkit import paint
from cadkit.export import TOP, write_svg
from hotrain import assembly, plates
from hotrain import layout as L
from hotrain.params import INCH, P, Params
from hotrain.parts import arch_half, bracket, cross_frame, end_pier, fit_test, handrail, keystone, tie_ladder

FROM_ROOM = ((0, 1, 0), (0, 0, 1))  # assembly seen from the room
CORNER_VIEW = ((-0.6, -1.0, 0.7), (0, 0, 1))


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
        if arch_half.mirrored(p):  # deck truss: an end half and a mirror-image start half per panel
            rows.append((f"arch_half_{tag}", arch_half.make(p, b), 2 * n, f"{n} bay(s) of {b:.1f} mm; end halves"))
            rows.append((f"arch_half_{tag}_start", arch_half.make(p, b, start=True), 2 * n,
                         f"{n} bay(s) of {b:.1f} mm; start halves (mirror image, rivets to the room)"))
        else:
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


def filament(p: Params, name: str) -> int:
    """Filament for a body: brown wood, white ceiling cleats, gray for everything else."""
    if name.endswith("_wood"):
        return p.filament_brown
    if name.startswith("ceiling_anchor"):
        return p.filament_white
    return p.filament_gray


def write_plates(pls: list, d: Path, csv_path: Path, preview_dir: Path | None = None, p: Params = P,
                 settings: Path | None = None, combined: str | None = None) -> None:
    """Each plate as STEP (painted) + Bambu Studio 3MF (a filament per color body) + the quantity sheet; with
    combined, also one project holding every plate (combined + .3mf). settings default: print_settings."""
    settings = settings or print_settings(p, d / "project_settings.json")
    cad_export.write_plates(pls, d, csv_path, lambda name: filament(p, name), preview_dir, settings=settings,
                            combined=combined)


def print_settings(p: Params, path: Path, **overrides) -> Path | None:
    """Your slicer settings (Bambu Studio) with this project's first layer (slow, and a hotter textured plate under
    PETG), plus any overrides (setting name -> value). None for another slicer: set those there by hand."""
    import json
    from cadkit import slicers
    from cadkit.settings import settings as cfg
    s = slicers.active()
    if s.name != "bambu":
        return None
    conf = json.loads(Path(cfg().slicer_settings or s.default_settings()).read_text())
    conf["initial_layer_speed"] = [f"{p.first_layer_speed:g}"]
    conf["initial_layer_infill_speed"] = [f"{p.first_layer_infill_speed:g}"]
    key = "textured_plate_temp_initial_layer"  # PETG slots: a hotter first layer; PLA keeps its own
    conf[key] = [f"{p.first_layer_bed_temp:g}" if kind == "PETG" else t
                 for kind, t in zip(conf["filament_type"], conf[key])]
    conf.update({k: str(v) for k, v in overrides.items()})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(conf, indent=4))
    return path


def fine_layer_settings(p: Params, path: Path) -> Path | None:
    """print_settings at the wire web's fine layers. None for another slicer: set the layer height there by hand."""
    return print_settings(p, path, layer_height=p.wire_layer, initial_layer_print_height=p.wire_first_layer)


def cmd_plates(p: Params, bays: list[float], out: Path, preview: bool) -> None:
    write_plates(plates.plates(p, bays) + plates.corner_plates(p), out / "plates", out / "plates.csv",
                 out / "preview" if preview else None, p=p, combined="near_ceiling_track")


def free_standing_bay(p: Params, bay_in: float = 16.0) -> list:
    """A 16" bay that stands on its own (a bracket at each end, end piers): for MakerWorld visitors, not this room
    (the room prints a bay at a time: `build sections`)."""
    return plates.all_in_one(p, [bay_in * INCH], name="free_standing_bay")


def makerworld_profiles(p: Params, d: Path) -> dict:
    """MakerWorld print profiles: {file name: (plates, slicer settings or None)}. The track variants a visitor can
    print without this room: a free-standing bay in each run style, the corners in each style, the wire-rail test."""
    from hotrain.plates import Plate
    D = replace(p, run_style="deck_truss")
    out = {"free_standing_bay_deck_truss": (free_standing_bay(D), None),
           "free_standing_bay_arch": (free_standing_bay(replace(p, run_style="arch")), None)}
    for style in ("pony", "bowstring"):
        out[f"corners_{style}"] = (plates.corner_plates(replace(D, corner_style=style)), None)
    out["wire_rail_test"] = (plates.wire_test_plates(p), fine_layer_settings(p, d / "fine_layers.json"))
    return out


def cmd_makerworld(p: Params, out: Path) -> Path:
    """One sliced project per print profile in out/makerworld/: every plate with its G-code and thumbnail, the files to
    upload to MakerWorld (as print profiles of one model). The upload itself is yours."""
    from concurrent.futures import ThreadPoolExecutor
    from cadkit import slicers
    s = slicers.active()
    d = out / "makerworld"
    work = d / "work"
    profiles = makerworld_profiles(p, work)
    for name, (pls, settings) in profiles.items():
        write_plates(pls, work / name, work / name / "plates.csv", p=p, settings=settings, combined=name)

    def finish(name):
        return name, s.slice_all(work / name / f"{name}{s.project_suffix}", d / f"{name}{s.project_suffix}")

    with ThreadPoolExecutor(len(profiles)) as ex:  # one slicer process per profile
        for name, reports in ex.map(finish, profiles):
            print(f"{name}: {len(reports)} plates sliced")
    return d


def cmd_wire_test(p: Params, out: Path) -> Path:
    """The stainless wire rail curve test: plates at fine layers, STEP of a piece with wires and a wheelset, and a
    render: out/wire_test/."""
    from build123d import Color
    from cadkit.render import render
    from hotrain.parts import wire_curve
    from hotrain.room import IRON, TIE_BROWN
    d = out / "wire_test"
    fine = fine_layer_settings(p, d / "fine_layers.json")
    if fine is None:
        print(f"set the slicer's layer height to {p.wire_layer} mm ({p.wire_first_layer} mm first layer) by hand")
    write_plates(plates.wire_test_plates(p), d, d / "plates.csv", p=p, settings=fine, combined="wire_test")
    b = wire_curve.bodies(p)
    steel, black = Color(0.78, 0.8, 0.83), Color(0.12, 0.12, 0.12)
    wheels = wire_curve.wheelset(p, p.wheel_d_rp25, 0.0)
    items = ([(b["wood"], TIE_BROWN), (b["steel"], IRON)] + [(w, steel) for w in wire_curve.wires(p)]
             + [(w, black) for w in wheels[:2]] + [(wheels[2], steel)])
    render(items, d / "render" / "wire_curve_test.png", view=(0.25, -1.0, 0.7), px=1600, tol=0.02, crop=True)
    for i, (s, c) in enumerate(items):
        s.label, s.color = ("wire_curve_wood", "wire_curve_steel", "wire", "wire", "wheel", "wheel", "axle")[i], c
    export(Compound(children=[s for s, _ in items], label="wire_curve_test_assembly"), out, "wire_curve_test_assembly",
           False, False, subdir="wire_test")
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


# (name, view target, view direction toward the eye, tessellation tolerance)
RENDERS = (
    ("bay_below", "run", (0.45, 1.0, -0.4), 0.1),  # one 16" bay, seen from the floor on the room side
    ("bay_above", "run", (0.45, 1.0, 0.55), 0.1),
    ("inside_corner", "inside", (-0.6, 1.0, -0.35), 0.1),
    ("bridge_corner", "bridge", (-0.6, 1.0, -0.35), 0.1),
    ("room", "room", (0.35, 0.6, 1.0), 0.5),
)


def _leaves(shape: Shape, color=None) -> list:
    """(solid, color) for every leaf of a colored Compound tree, each taking its nearest colored ancestor's color."""
    color = shape.color or color
    kids = list(shape.children) if isinstance(shape, Compound) else []
    if not kids:
        return [(shape, color)]
    return [leaf for k in kids for leaf in _leaves(k, color)]


def cmd_render(p: Params, out: Path) -> list[Path]:
    from cadkit.render import render
    from hotrain import view
    paths = []
    for name, tgt, eye, tol in RENDERS:
        path = out / "render" / f"{name}.png"
        render(_leaves(view.target(p, tgt)), path, view=eye, tol=tol, crop=True)
        paths.append(path)
    return paths


def cmd_sections(p: Params, out: Path) -> Path:
    """The room a bay at a time: out/sections/<section>/<section>.3mf (every plate of one bay's kit as tabs) and
    sections.csv (each kit, how many bays print it, and which bays)."""
    d = out / "sections"
    rows = []
    for sec in plates.sections(p):
        sd = d / sec.name
        pls = plates.section_plates(p, sec)
        write_plates(pls, sd, sd / "plates.csv", p=p, combined=sec.name)
        rows.append([sec.name, sec.qty, len(pls), "; ".join(f"{run} bay {i}" for run, i in sec.where)])
    with open(d / "sections.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["section", "print", "plates", "bays"])
        w.writerows(rows)
    return d


def cmd_latch_test(p: Params, out: Path) -> Path:
    """The latch coupon on its own plate: out/latch_test/."""
    from hotrain.plates import Plate
    d = out / "latch_test"
    write_plates([Plate("latch_test", 1, [("latch_test", fit_test.latch_coupon(p))])], d, d / "plates.csv", p=p)
    return d


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
                                        "check", "render", "wire-test", "makerworld", "latch-test", "sections"])
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
    if a.command in ("room", "glb", "web") or (a.command, a.target) == ("show", "room"):
        from hotrain import room
        for note in room.misfit_notes():
            print(note)
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
    if a.command == "sections":
        print(f"wrote {cmd_sections(p, out)}/ (sections.csv: each bay kit and how many times to print it)")
        return 0
    if a.command == "latch-test":
        print(f"wrote {cmd_latch_test(p, out)}/ (one plate: latch_test)")
        return 0
    if a.command == "makerworld":
        d = cmd_makerworld(p, out)
        print(f"wrote {d}/: one sliced project per print profile, ready to upload")
        return 0
    if a.command == "wire-test":
        d = cmd_wire_test(p, out)
        print(f"wrote {d}/ (plates.csv lists what to print; the plates open at {p.wire_layer} mm layers)")
        return 0
    if a.command == "render":
        for path in cmd_render(p, out):
            print(path)
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
