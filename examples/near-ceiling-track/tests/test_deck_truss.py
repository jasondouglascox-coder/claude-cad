"""Deck-truss straight runs (run_style="deck_truss"): panel shape, pier, mid-bay splice key, cross-frames."""
from dataclasses import replace

import pytest
from build123d import Align, Box, Mesher, Pos

from hotrain import assembly
from hotrain import layout as L
from hotrain.checks import printable_problems
from hotrain.params import INCH, P
from hotrain.parts import arch_half, cross_frame, keystone

D = replace(P, run_style="deck_truss")
BAY = 16 * INCH


def _cut(part, y: float):
    """Solids cut by a thin full-length horizontal probe at print height y (print Y 0 = pier bottom)."""
    bb = part.bounding_box()
    probe = Pos(bb.min.X - 1, y, bb.min.Z - 1) * Box(bb.size.X + 2, 0.2, bb.size.Z + 2,
                                                     align=(Align.MIN, Align.MIN, Align.MIN))
    return (part & probe).solids()


def _y(z: float) -> float:
    """Assembly z (tie underside = 0) -> print Y of a panel."""
    return z + D.pier_depth


def test_arch_is_still_the_default():
    assert P.run_style == "arch"


def test_unknown_run_style_is_rejected():
    with pytest.raises(ValueError):
        arch_half.profile(replace(P, run_style="nope"), BAY)


@pytest.mark.parametrize("bay", [D.min_bay_len, BAY, D.max_bay_len])
def test_deck_panel_printable_and_meshes(bay, tmp_path):
    part = arch_half.make(D, bay)
    assert printable_problems(part) == []
    m = Mesher()
    m.add_shape(part)
    m.write(str(tmp_path / "half.3mf"))


def test_pier_keeps_full_depth_and_truss_is_shallower():
    part = arch_half.make(D, BAY)
    bb = part.bounding_box()
    assert bb.min.Y == pytest.approx(0, abs=1e-6)  # pier bottom
    # just above the truss bottom only the pier is cut; just below the deck the top chord spans the half
    pier_only = _cut(part, _y(-D.dt_depth) - 2)
    assert len(pier_only) == 1 and pier_only[0].bounding_box().max.X < L.springing_u(D) + D.pier_batter + 0.5


def test_bottom_chord_at_truss_depth_past_first_post():
    part = arch_half.make(D, BAY)
    foot = L.post_us(D, BAY)[0]
    chord = [s for s in _cut(part, _y(-D.dt_depth) + D.rib_notch + 0.5) if s.bounding_box().min.X > L.springing_u(D) + 5]
    assert len(chord) == 1
    cb = chord[0].bounding_box()
    assert cb.min.X <= foot and cb.max.X == pytest.approx(BAY / 2, abs=1e-6)


def test_warren_web_member_count():
    """Mid-depth cut: pier, inclined end post, one diagonal per panel, an upright per post after the
    foot, and the mid-bay post."""
    part = arch_half.make(D, BAY)
    posts = L.post_us(D, BAY)
    n_panels = len(posts)  # foot -> ... -> mid-bay
    expected = 1 + 1 + n_panels + (len(posts) - 1) + 1
    assert len(_cut(part, _y(-D.dt_depth / 2))) == expected


def test_top_chord_continuous():
    part = arch_half.make(D, BAY)
    assert len(_cut(part, _y(-D.top_band_h / 2))) == 1


def test_rib_low_follows_end_post_then_bottom_chord():
    s, posts = L.springing_u(D), L.post_us(D, BAY)
    assert L.rib_low(D, BAY, s / 2) == pytest.approx(-D.pier_depth)
    for u in posts + [BAY / 2 - 1]:
        assert L.rib_low(D, BAY, u) == pytest.approx(-D.dt_depth)
    mid = (s + D.pier_batter + posts[0]) / 2
    assert -D.dt_depth < L.rib_low(D, BAY, mid) < -D.top_band_h


def test_cross_frame_notch_leaves_chord_wall():
    nw = (D.cf_t + D.fit_slide) / 2
    for u in L.post_us(D, BAY):
        top = -L.cf_depth(D, BAY, u) + D.rib_notch
        assert top - L.rib_low(D, BAY, u) == pytest.approx(D.rib_notch)
        assert top < -D.dt_depth + D.dt_chord_h - 1.5  # notch stays in the bottom chord


def test_splice_key_is_small_and_low():
    kb = keystone.make(D).bounding_box()
    assert kb.size.X == pytest.approx(D.dt_key_len) and kb.size.Y == pytest.approx(D.dt_key_head)
    assert keystone.key_z(D) - D.dt_key_head / 2 >= -D.dt_depth + 1.5  # wall under the socket
    assert keystone.key_z(D) + D.dt_key_head / 2 <= -D.dt_depth + D.dt_gusset_h - 1.5


def test_mid_bay_post_is_slim():
    """Above the splice plate, the mid-bay end of a half is only dt_mid_w wide."""
    part = arch_half.make(D, BAY)
    z = -D.dt_depth + D.dt_gusset_h + 6
    last = max(_cut(part, _y(z)), key=lambda s: s.bounding_box().max.X)
    assert last.bounding_box().max.X == pytest.approx(BAY / 2, abs=1e-6)
    assert last.bounding_box().size.X == pytest.approx(D.dt_mid_w, abs=0.05)


def test_cross_frame_has_x_brace():
    d = L.cf_depth(D, BAY, L.post_us(D, BAY)[1])
    cf = cross_frame.make(D, d)
    assert printable_problems(cf) == []
    bb = cf.bounding_box()
    # a vertical probe down the track center line: top border, each X crossing, bottom bar
    x = -cross_frame.y_min(D)
    probe = Pos(x - 0.1, bb.min.Y - 1, -1) * Box(0.2, bb.size.Y + 2, 10, align=(Align.MIN, Align.MIN, Align.MIN))
    n = cross_frame.x_cells(D, d)
    assert n >= 2
    assert len((cf & probe).solids()) == n + 2
    arch = cross_frame.make(P, d)
    assert len((arch & probe).solids()) == 2  # arch style keeps the open window


@pytest.mark.slow
@pytest.mark.parametrize("bays", [[BAY], [D.min_bay_len, D.max_bay_len]])
def test_deck_truss_assembly_has_no_clashes(bays):
    assert assembly.find_clashes(assembly.placed_parts(D, bays)) == []


def test_cli_style_overrides():
    import argparse
    from hotrain.build import params_from_args
    p = params_from_args(argparse.Namespace(run_style="deck_truss", corner_style="bowstring"))
    assert (p.run_style, p.corner_style) == ("deck_truss", "bowstring")
    assert params_from_args(argparse.Namespace(run_style=None, corner_style=None)) == P


@pytest.mark.parametrize("bay", [D.min_bay_len, D.max_bay_len])
def test_deck_halves_nest_on_one_plate(bay):
    from hotrain import plates
    pair = plates.nested_arch_pair(D, bay)
    a, b = pair.solids()
    bb = pair.bounding_box()
    assert bb.min.Z == pytest.approx(0, abs=1e-6)
    assert max(bb.size.X, bb.size.Y) <= D.bed_usable - D.bed_margin  # packed either way round, a margin to spare
    assert a.distance_to(b) >= plates.GAP - 1e-3


# ---- short walkway railing --------------------------------------------------------------------------

def _handrails(p):
    return [s for n, s in assembly.placed_parts(p, [BAY]) if n.startswith("handrail")]


def test_deck_railing_is_short_single_bar():
    from hotrain.parts import handrail
    piece = L.handrail_pieces(D, [BAY])[0]
    hr = handrail.make(D, piece)
    assert hr.bounding_box().max.Y == pytest.approx(D.rail_top + D.dt_handrail_h)
    # a vertical probe between posts crosses only the top bar
    x = (piece.posts[0] + piece.posts[1]) / 2 - piece.x_start
    probe = Pos(x - 0.1, -1, -1) * Box(0.2, 100, 10, align=(Align.MIN, Align.MIN, Align.MIN))
    assert len((hr & probe).solids()) == 1
    arch = handrail.make(P, L.handrail_pieces(P, [BAY])[0])
    assert len((arch & probe).solids()) == 2  # arch keeps top + mid bar
    assert arch.bounding_box().max.Y == pytest.approx(P.rail_top + P.handrail_h)


@pytest.mark.slow
def test_tipping_car_is_caught_by_short_railing():
    from hotrain.checks import tip_catch_angle
    a = tip_catch_angle(D, _handrails(D), BAY)
    assert a is not None and a <= 25.0


@pytest.mark.slow
def test_tip_check_can_fail():
    """A railing barely above the rail head only touches the car once it is past the 25 degree limit."""
    from hotrain.checks import tip_catch_angle
    low = replace(D, dt_handrail_h=1.5)
    a = tip_catch_angle(low, _handrails(low), BAY)
    assert a is None or a > 25.0


@pytest.mark.parametrize("bay", [D.min_bay_len, BAY, D.max_bay_len])
def test_end_post_top_is_buried_in_chord_and_cap(bay):
    """Both corners of the end post's square-cut top end lie inside the top chord or the pier cap."""
    import math
    (ax, az), (bx, bz) = arch_half.end_post(D, bay)
    dx, dz = bx - ax, bz - az
    n = math.hypot(dx, dz)
    ox, oz = -dz / n * D.dt_post_w / 2, dx / n * D.dt_post_w / 2
    s, tb = L.springing_u(D), D.top_band_h
    zc = -tb - D.pier_cap_h
    for x, z in ((ax + ox, az + oz), (ax - ox, az - oz)):
        in_chord = 0 <= x <= bay / 2 and -tb <= z <= 0
        in_cap = 0 <= x <= s + D.pier_cap_out and zc <= z <= -tb + D.dt_lap
        assert in_chord or in_cap, (x, z)
