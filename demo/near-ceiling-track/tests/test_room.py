import math

import pytest

from hotrain import layout as L
from hotrain import room
from hotrain.params import INCH, P

pytestmark = pytest.mark.slow  # minutes per test: run with -m slow or the full suite


@pytest.fixture(scope="module")
def secs():
    return room.sections(P, room.Room())


def test_track_is_continuous_wall_to_wall(secs):
    ends = [room.track_ends(P, s) for s in secs]
    for (_, b), (a, _) in zip(ends, ends[1:]):
        assert math.dist(a, b) < 0.01


def test_runs_are_printable_bays_ending_at_corners(secs):
    runs = [s for s in secs if s.kind == "run"]
    assert [s.ends for s in runs] == [(L.FREE, L.CORNER), (L.CORNER, L.CORNER), (L.CORNER, L.FREE)]
    for s in runs:
        L.validate_bays(P, list(s.bays))


def test_track_hugs_the_walls(secs):
    r = room.Room()
    xr = (r.alcove_w + r.back_len) * INCH
    yb = (r.right_len - r.alcove_depth) * INCH
    (a, _), (_, b) = room.track_ends(P, secs[0]), room.track_ends(P, secs[1])
    assert a[0] == pytest.approx(xr - P.track_offset)  # right wall
    assert b == pytest.approx((r.back_len * INCH, yb - P.track_offset))  # bridge lands on the bump-out corner
    _, c = room.track_ends(P, secs[-1])
    assert c[0] == pytest.approx(P.track_offset)  # left wall


def test_rail_top_twelve_inches_below_ceiling(secs):
    r = room.Room()
    tops = [rail.bounding_box().max.Z for s in secs for rail in room.rails(P, s)]
    assert max(tops) == pytest.approx((r.ceiling - r.rail_below_ceiling) * INCH, abs=0.01)
    assert min(tops) == pytest.approx(max(tops), abs=0.01)


def test_nothing_inside_walls_or_doors(secs):
    walls = [w for _, w, _ in room.walls(room.Room())]
    for s in secs:
        for n, part in room.section_parts(P, s):
            pb = part.bounding_box()
            for w in walls:
                wb = w.bounding_box()
                if (pb.min.X < wb.max.X and wb.min.X < pb.max.X and pb.min.Y < wb.max.Y
                        and wb.min.Y < pb.max.Y and pb.min.Z < wb.max.Z and wb.min.Z < pb.max.Z):
                    assert (part & w).volume < 1e-6, f"{s.name}/{n} goes into a wall"


def test_room_step_has_colors(tmp_path):
    from hotrain import build
    assert build.main(["room", "--out", str(tmp_path)]) == 0
    text = (tmp_path / "step" / "office.step").read_text()
    assert "COLOUR_RGB" in text and "wall_right" in text and "bridge_corner" in text
    teal = tuple(round(v, 3) for v in (0xad / 255, 0xf7 / 255, 0xf5 / 255))
    import re
    colors = {tuple(round(float(v), 3) for v in m) for m in re.findall(r"COLOUR_RGB\('',([\d.]+),([\d.]+),([\d.]+)\)", text)}
    assert teal in colors


def test_glb_export_one_file_per_section(tmp_path, monkeypatch):
    names = [n for n, _ in room.section_models(P)]
    assert names == ["right_viaduct", "bridge_corner", "back_viaduct", "inside_corner", "left_viaduct", "room"]


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
