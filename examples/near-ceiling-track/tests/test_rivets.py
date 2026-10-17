"""Rivet heads on the deck truss: gray bumps on the face that looks into the room, printed on top of the flat panel.
Each panel is a start half and an end half; the start half prints as the mirror image so its rivets face the room
too. The arch style and the corners get none."""
import math
from dataclasses import replace
from functools import lru_cache

import pytest
from build123d import Align, Box, Pos

from cadkit.checks import off_layer_z, open_edges, printable_problems
from hotrain import assembly
from hotrain import layout as L
from hotrain.params import INCH, P
from hotrain.parts import arch_half

D = replace(P, run_style="deck_truss")
BAY = 16 * INCH


@lru_cache(maxsize=None)
def half(start: bool):
    return arch_half.make(D, BAY, start=start)


def test_rivets_sit_on_the_top_face_on_layers():
    for start in (False, True):
        part = half(start)
        assert printable_problems(part, D.printer) == []
        assert open_edges(part) == 0
        assert off_layer_z(part, D.printer) == []
        assert part.bounding_box().max.Z == pytest.approx(D.panel_t + D.printer.layers(D.rivet_h))


def test_rivets_are_many_and_all_on_truss_members():
    pts = arch_half.rivet_points(D, BAY)
    assert len(pts) > 150
    body = arch_half.make(replace(D, rivet_d=0.0), BAY)  # the bare panel
    r = D.rivet_d / 2
    for u, z in pts:
        for du, dz in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r)):  # the whole head stands on the panel
            assert body.is_inside((u + du, z + dz + D.pier_depth, D.panel_t / 2)), (u, z)
    s = L.springing_u(D) + D.pier_cap_out
    assert min(u for u, _ in pts) > s, "no rivets on the concrete-look pier"


def test_rivets_never_touch_each_other():
    pts = arch_half.rivet_points(D, BAY)
    gap = D.rivet_d + 0.3
    for i, (a, b) in enumerate(pts):
        for c, d in pts[i + 1:]:
            assert (a - c) ** 2 + (b - d) ** 2 >= gap ** 2 - 1e-9


def test_start_half_is_the_mirror_image_in_the_same_place():
    """The mirrored start half placed fills exactly the space the old start half did, plus its rivet heads."""
    bare = replace(D, rivet_d=0.0)
    old = arch_half.place(bare, 0, BAY, 10.0, end=False) * arch_half.make(bare, BAY)
    new = arch_half.place_half(D, 0, BAY, 10.0, start=True) * half(True)
    heads = len(arch_half.rivet_points(D, BAY)) * math.pi * (D.rivet_d / 2) ** 2 * D.printer.layers(D.rivet_h)
    assert (old - new).volume == pytest.approx(0, abs=1e-3)
    assert (new - old).volume == pytest.approx(heads, rel=0.02)


def test_rivets_off_gives_flat_panels():
    """rivet_d = 0 turns the heads off; the panels keep their mirrored start halves (the user's choice)."""
    bare = replace(D, rivet_d=0.0)
    assert arch_half.rivet_points(bare, BAY) == []
    for start in (False, True):
        assert arch_half.make(bare, BAY, start=start).bounding_box().max.Z == pytest.approx(D.panel_t)


@pytest.mark.parametrize("start", [False, True])
def test_both_halves_show_their_rivets_to_the_room(start):
    """Room is +Y. The rivets stand proud of the panel's +Y face, on both panels of a bay."""
    y_c = max(D.rail_ys)
    placed = arch_half.place_half(D, 0, BAY, y_c, start=start) * half(start)
    face = y_c + D.panel_t / 2
    probe = Pos(-1, face + 0.05, -D.pier_depth - 1) * Box(BAY + 2, D.rivet_h, D.pier_depth + 10,
                                                        align=(Align.MIN, Align.MIN, Align.MIN))
    assert len((placed & probe).solids()) > 150
    back = Pos(-1, y_c - D.panel_t / 2 - 0.05 - D.rivet_h, -D.pier_depth - 1) * Box(
        BAY + 2, D.rivet_h, D.pier_depth + 10, align=(Align.MIN, Align.MIN, Align.MIN))
    assert (placed & back).volume == pytest.approx(0, abs=1e-6)


def test_assembly_uses_a_start_and_an_end_half_per_panel():
    names = [n for n, _ in assembly.placed_parts(D, [BAY])]
    assert sum(n.endswith("_arch_start") for n in names) == 2 and sum(n.endswith("_arch_end") for n in names) == 2
    shapes = dict(assembly.placed_parts(D, [BAY]))
    assert shapes["bay0_room_arch_start"].label.endswith("_start")
    assert not shapes["bay0_room_arch_end"].label.endswith("_start")


def test_each_half_span_plate_prints_one_of_each_half():
    from hotrain import plates
    pair = plates.nested_arch_pair(D, BAY)
    assert sorted(c.label for c in pair.children) == [f"arch_half_{BAY:.1f}mm", f"arch_half_{BAY:.1f}mm_start"]
    bb = pair.bounding_box()
    assert bb.size.X <= D.bed_usable and bb.size.Y <= D.bed_usable


def test_arch_style_has_no_rivets_and_one_half():
    a = arch_half.make(P, BAY)
    assert a.bounding_box().max.Z == pytest.approx(P.panel_t)
    assert arch_half.rivet_points(P, BAY) == []


@pytest.mark.slow
def test_bambu_prints_the_rivet_heads(tmp_path):
    """Bambu drops features it can't extrude (the first wire-rail lip vanished): the pair of halves slices with
    layers up to the rivet tops, and the head layers carry hundreds of tiny loops."""
    import zipfile
    from cadkit import slicers
    from hotrain import build, plates
    from hotrain.plates import Plate
    s = slicers.active()
    if not s.available():
        pytest.skip("no slicer installed (settings: slicer)")
    pl = Plate("pair", 1, plates.pack(D, [("arch_half_pair", plates.nested_arch_pair(D, BAY))])[0])
    build.write_plates([pl], tmp_path, tmp_path / "p.csv", p=D)
    rep = s.slice_report(tmp_path / f"pair{s.project_suffix}", tmp_path / f"s{s.project_suffix}")
    top = D.panel_t + D.printer.layers(D.rivet_h)
    assert rep["layers"][-1][2] == round(top / D.printer.layer) - 1
    if s.name == "bambu":
        g = zipfile.ZipFile(tmp_path / f"s{s.project_suffix}").read("Metadata/plate_1.gcode").decode()
        last = g.split(f"; Z_HEIGHT: {top:g}")[1]
        assert last.count("; FEATURE: Outer wall") + last.count("G1") > 2 * len(arch_half.rivet_points(D, BAY))


def test_no_rivet_under_a_cross_frame():
    """Cross-frames grip both panels at every post (the clash test caught heads inside their slots)."""
    clear = (D.cf_t + D.fit_slide) / 2 + D.rivet_d / 2
    for u, _ in arch_half.rivet_points(D, BAY):
        assert all(abs(u - post) >= clear for post in L.post_us(D, BAY)), u
