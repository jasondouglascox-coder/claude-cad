import math

import pytest

from hotrain import layout as L
from hotrain import room
from hotrain.params import INCH, P

@pytest.fixture(scope="module")
def secs():
    return room.sections(P, room.Room())


def test_track_is_a_closed_loop(secs):
    ends = [room.track_ends(P, s) for s in secs]
    for (_, b), (a, _) in zip(ends, ends[1:] + ends[:1]):
        assert math.dist(a, b) < 0.01


def test_loop_has_three_inside_corners_and_a_bridge(secs):
    assert [s.kind for s in secs if s.kind != "run"] == ["bridge", "inside", "inside", "inside"]


def test_runs_are_printable_bays_ending_at_corners(secs):
    runs = [s for s in secs if s.kind == "run"]
    assert len(runs) == 4
    for s in runs:
        assert s.ends == (L.CORNER, L.CORNER)
        L.validate_bays(P, list(s.bays))


def test_track_hugs_the_walls(secs):
    r = room.Room()
    o = P.track_offset
    xr = (r.alcove_w + r.back_len) * INCH
    yb = (r.right_len - r.alcove_depth) * INCH
    by = {s.name: room.track_ends(P, s) for s in secs}
    (a, b) = by["right_viaduct"]
    assert a[0] == pytest.approx(xr - o) and b[0] == pytest.approx(xr - o)  # right wall
    assert by["bridge_corner"][1] == pytest.approx((r.back_len * INCH, yb - o))  # lands on the bump-out corner
    for pt in by["back_viaduct"]:
        assert pt[1] == pytest.approx(yb - o)  # back wall
    for pt in by["left_viaduct"]:
        assert pt[0] == pytest.approx(o)  # left wall
    for pt in by["front_viaduct"]:
        assert pt[1] == pytest.approx(o)  # front wall (not modeled)


def test_misfit_compares_measured_walls_with_the_model():
    r = room.Room(right_len=170, alcove_w=43.75, alcove_depth=43.75, back_len=82.5,
                  front_len=125.875, left_len=126.375)
    assert r.misfit() == pytest.approx({"front": 0.375, "left": -0.125})  # model minus measured, inches
    notes = room.misfit_notes(r)  # past a tape's 1/8"
    assert len(notes) == 1 and "front" in notes[0]


@pytest.mark.slow
def test_rail_top_twelve_inches_below_ceiling(secs):
    r = room.Room()
    tops = [rail.bounding_box().max.Z for s in secs for rail in room.rails(P, s)]
    assert max(tops) == pytest.approx((r.ceiling - r.rail_below_ceiling) * INCH, abs=0.01)
    assert min(tops) == pytest.approx(max(tops), abs=0.01)


@pytest.mark.slow
def test_nothing_inside_walls_or_doors(secs):
    walls = [w for _, w, _ in room.walls(room.Room())] + [room.front_wall(room.Room())]
    for s in secs:
        for n, part in room.section_parts(P, s):
            pb = part.bounding_box()
            for w in walls:
                wb = w.bounding_box()
                if (pb.min.X < wb.max.X and wb.min.X < pb.max.X and pb.min.Y < wb.max.Y
                        and wb.min.Y < pb.max.Y and pb.min.Z < wb.max.Z and wb.min.Z < pb.max.Z):
                    assert (part & w).volume < 1e-6, f"{s.name}/{n} goes into a wall"


@pytest.mark.slow
def test_room_step_has_colors(tmp_path):
    from hotrain import build
    assert build.main(["room", "--out", str(tmp_path)]) == 0
    text = (tmp_path / "step" / "office.step").read_text()
    assert "COLOUR_RGB" in text and "wall_right" in text and "bridge_corner" in text
    teal = tuple(round(v, 3) for v in (0xad / 255, 0xf7 / 255, 0xf5 / 255))
    import re
    colors = {tuple(round(float(v), 3) for v in m) for m in re.findall(r"COLOUR_RGB\('',([\d.]+),([\d.]+),([\d.]+)\)", text)}
    assert teal in colors


@pytest.mark.slow
def test_glb_export_one_file_per_section(tmp_path, monkeypatch):
    names = [n for n, _ in room.section_models(P)]
    assert names == [s.name for s in room.sections(P)] + ["room"]
    assert set(room.LOAD_ORDER) == set(names) == set(room.LABELS)


def test_glb_to_json_is_self_contained(tmp_path):
    import json
    from build123d import Box, Compound, export_gltf
    b = Box(10, 10, 10)
    b.color = room.TEAL
    glb = tmp_path / "b.glb"
    export_gltf(Compound(children=[b]), str(glb), binary=True)
    room.glb_to_json(glb, tmp_path / "b.json")
    doc = json.loads((tmp_path / "b.json").read_text())
    assert doc["buffers"][0]["uri"].startswith("data:application/octet-stream;base64,")
    assert doc["materials"], "colors survive as materials"
