import pytest

from hotrain.params import P
from hotrain.parts import fit_test


def test_fit_test_fits_bed_and_has_every_piece():
    ft = fit_test.make(P)
    bb = ft.bounding_box()
    assert bb.max.X <= P.bed_usable and bb.max.Y <= P.bed_usable
    assert bb.min.Z == pytest.approx(0, abs=1e-6)
    solids = ft.solids()
    assert all(s.is_valid for s in solids)
    assert len(solids) == 3 + 2 + 3 + 1 + 2 + 3 + 3  # grooves, slot plate + tab strip, key blocks, key, latch pair,
    #                                                   rod snaps, rivet strips


def test_groove_variants_marked_distinctly():
    vols = [fit_test.groove_sample(P, 0.2, n).volume for n in (1, 2, 3)]
    assert vols[0] - vols[1] > 0.3 and vols[1] - vols[2] > 0.3


@pytest.mark.parametrize("k", range(3))
def test_rivet_strips_carry_two_rows_of_heads_of_their_size(k):
    """A strip per head size (the deck truss uses rivet_d) to see size and PETG stringing before printing panels."""
    from build123d import Align, Box, Pos
    from cadkit.checks import off_layer_z, printable_problems
    d = fit_test.RIVET_SIZES[k]
    strip = fit_test.rivet_strip(P, d, k + 1)
    assert printable_problems(strip, P.printer) == [] and off_layer_z(strip, P.printer) == []
    bb = strip.bounding_box()
    heads = (strip & Pos(bb.min.X - 1, bb.min.Y - 1, P.panel_t + 0.05) * Box(bb.size.X + 2, bb.size.Y + 2, 1,
                                                                            align=(Align.MIN,) * 3)).solids()
    assert len(heads) == 2 * fit_test.rivet_count(P)
    assert all(h.bounding_box().size.X == pytest.approx(d, abs=0.02) for h in heads)
    assert bb.max.Z == pytest.approx(P.panel_t + P.printer.layers(P.rivet_h))


def test_the_parts_use_the_variants_picked_from_the_print():
    """2026-10-26 fit test: keystone 1, tab slot 1, rivets 1 (0.6 mm: the larger heads didn't come out smooth)."""
    assert P.fit_key == fit_test.KEY_FITS[0]
    assert P.fit_tab == fit_test.SLOT_FITS[0]
    assert P.rivet_d == fit_test.RIVET_SIZES[0]


def test_rails_use_groove_2_and_the_notch_1_clips():
    """2026-11-04: coupon 6's groove 2 and coupon 7's notch-1 clips, as tested: same depth, same clip shape."""
    assert P.fit_rail == fit_test.CHANNEL_FITS[1]
    assert P.clip_reach == fit_test.CHANNEL_LIPS[0]
    assert P.rail_sink == fit_test.CHANNEL_DEPTH


@pytest.mark.parametrize("k", range(3))
def test_rail_channels_press_the_base_in(k):
    """Coupon 6 (2026-11-04: coupon 4's 1- and 2-notch hooks were best, but the ties are flimsy; coupon 5's channels,
    0.0 to -0.10, were all way loose): no ties, a solid
    gray bar with a channel the rail base presses into, CHANNEL_FITS wide of it (1-3 notches at one end), its top
    edges chamfered as a lead-in. The channel is as deep as the shoulders, its floor where the tie plates' are."""
    from build123d import Align, Box, Pos
    from cadkit.checks import downward_faces, off_layer_z, printable_problems
    c = fit_test.rail_channel_coupon(P)
    assert printable_problems(c, P.printer) == [] and off_layer_z(c, P.printer) == []
    assert downward_faces(c) == []
    bb = c.bounding_box()
    assert bb.size.Z == pytest.approx(fit_test.CHANNEL_FLOOR + fit_test.CHANNEL_DEPTH)
    assert bb.size.X == pytest.approx(fit_test.CHANNEL_LEN)

    def gaps(z, x):  # widths of the openings across the bar at (x, z)
        cut = c & Pos(x, bb.min.Y - 1, z) * Box(0.1, bb.size.Y + 2, 0.02, align=(Align.MIN,) * 3)
        ys = sorted((s.bounding_box() for s in cut.solids()), key=lambda b: b.min.Y)
        return [q.min.Y - p.max.Y for p, q in zip(ys, ys[1:])]
    w = P.rail_base_w + fit_test.CHANNEL_FITS[k]
    floor = fit_test.CHANNEL_FLOOR
    assert gaps(floor + 0.1, bb.size.X / 2)[k] == pytest.approx(w, abs=0.01)  # pressing on the base edge
    assert gaps(floor + P.rail_base_edge - 0.02, bb.size.X / 2)[k] == pytest.approx(w, abs=0.01)
    assert gaps(bb.max.Z - 0.03, bb.size.X / 2)[k] > w + 0.2  # the lead-in
    notches = [g for g in gaps(floor + 0.1, 0.5) if g < P.rail_base_w / 2]  # in the x = 0 end, beside each channel
    assert len(notches) == 1 + 2 + 3
    assert fit_test.CHANNEL_FITS == tuple(sorted(fit_test.CHANNEL_FITS, reverse=True))  # tighter with each notch


def test_rail_channel_coupon_is_gray_only(tmp_path):
    from cadkit import slicers
    from cadkit.plates import colors_used
    from hotrain import build
    c = fit_test.rail_channel_coupon(P)
    assert len(c.solids()) == 1 and colors_used([("c", c)]) == 1
    assert build.main(["rail-channel-test", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "rail_channel_test" / f"rail_channel_test{slicers.active().project_suffix}").exists()


@pytest.mark.parametrize("k", range(3))
def test_rail_lips_over_groove_2(k):
    """Coupon 7 (2026-11-04: coupon 6's groove 2 held the base well side to side): that channel three times, sunk in
    a brown bar (the rail down in the wood), with short gray clips on top both sides at the lip ties' spacing,
    reaching CHANNEL_LIPS past the wall (1-3 notches), shaped like coupon 4's 1-notch hooks: from the channel top,
    the underside rising to a one-layer tip, a sloped lead-in."""
    from build123d import Align, Box, Pos
    from cadkit.checks import downward_faces, off_layer_z, printable_problems
    wood, steel = fit_test.rail_lip_coupon(P).children
    c = wood + steel
    assert printable_problems(c, P.printer) == [] and off_layer_z(c, P.printer) == []
    assert downward_faces(c) == []
    bb = c.bounding_box()
    top, rise, over = fit_test.CHANNEL_FLOOR + fit_test.CHANNEL_DEPTH, P.clip_rise, fit_test.CHANNEL_LIPS[k]
    w = P.rail_base_w + fit_test.CHANNEL_FITS[1]

    def cut(z, x0=bb.min.X - 1, dx=bb.size.X + 2):
        return c & Pos(x0, bb.min.Y - 1, z) * Box(dx, bb.size.Y + 2, 0.02, align=(Align.MIN,) * 3)

    def gaps(z, x):
        ys = sorted((s.bounding_box() for s in cut(z, x, 0.1).solids()), key=lambda b: b.min.Y)
        return [q.min.Y - p.max.Y for p, q in zip(ys, ys[1:])]

    tips = cut(top + rise + 0.05).solids()
    assert len(tips) == len(steel.solids()) == 3 * 2 * 2  # channels, sides, clips
    x = min(t.center().X for t in tips)
    assert gaps(fit_test.CHANNEL_FLOOR + 0.1, x)[k] == pytest.approx(w, abs=0.01)
    assert gaps(top - 0.03, x)[k] == pytest.approx(w, abs=0.01)  # no flare: the lip's top is the lead-in
    assert gaps(top + rise + 0.05, x)[2 * k] == pytest.approx(w - 2 * over, abs=0.01)  # above the bar: lips only
    assert gaps(top + rise + P.clip_tip + 0.05, x)[2 * k] > w - 2 * over + 0.05
    xs = sorted({round(t.center().X, 3) for t in tips})
    assert xs[1] - xs[0] == pytest.approx(fit_test.CLIP_SPAN)
    assert bb.max.Z == pytest.approx(top + P.clip_h)
    assert fit_test.CHANNEL_FLOOR + P.rail_height - bb.max.Z >= 1.1  # well under the wheels' flanges
    notches = [g for g in gaps(fit_test.CHANNEL_FLOOR + 0.1, 0.5) if g < P.rail_base_w / 2]
    assert len(notches) == 1 + 2 + 3


def test_rail_lip_coupon_is_brown_with_gray_clips(tmp_path):
    from cadkit import slicers
    from cadkit.checks import unsupported
    from cadkit.plates import color_changes
    from hotrain import build
    wood, steel = fit_test.rail_lip_coupon(P).children
    top = fit_test.CHANNEL_FLOOR + fit_test.CHANNEL_DEPTH
    assert len(wood.solids()) == 1 and wood.bounding_box().max.Z == pytest.approx(top)
    assert steel.bounding_box().min.Z == pytest.approx(top)
    probe, sides = 0.1, 2 * 2  # every clip sits on brown; only its underside's rise leans out over the channel
    sliver = sum(o * probe ** 2 / (2 * P.clip_rise) * P.tie_w * sides for o in fit_test.CHANNEL_LIPS)  # tie-wide
    assert unsupported(steel, wood, probe) == pytest.approx(sliver, rel=1e-3)
    assert color_changes([("w", wood), ("s", steel)], P.printer) == 1
    assert build.main(["rail-lip-test", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "rail_lip_test" / f"rail_lip_test{slicers.active().project_suffix}").exists()


def test_tie_ladder_tab_slot_is_the_picked_fit():
    """Across the ladder, a tab slot is the truss panel plus fit_tab."""
    from build123d import Align, Box, Pos
    from hotrain import layout as L
    from hotrain.params import INCH
    from hotrain.parts import tie_ladder
    bays = [16 * INCH]
    seg = L.segments(P, bays)[1]
    lad = tie_ladder.make(P, bays, seg)
    x = next(x for x in L.tab_xs(P, bays) if seg.x_start + 5 < x < seg.x_end - 5) - seg.x_start
    y_rail = max(P.rail_ys) + P.tie_l / 2  # the slot sits under the rail, in the runner
    probe = Pos(x - 0.05, y_rail - 5, 0.3) * Box(0.1, 10, 0.2, align=(Align.MIN,) * 3)
    pieces = sorted((s.bounding_box() for s in (lad & probe).solids()), key=lambda b: b.min.Y)
    gaps = [b.min.Y - a.max.Y for a, b in zip(pieces, pieces[1:])]
    assert min(gaps, key=lambda g: abs(g - P.panel_t - P.fit_tab)) == pytest.approx(P.panel_t + P.fit_tab, abs=0.01)


def test_keystone_socket_is_the_picked_fit():
    """At the panel edge the socket opens exactly the key's waist plus fit_key each side."""
    from dataclasses import replace
    from build123d import Align, Box, Pos
    from hotrain import layout as L
    from hotrain.params import INCH
    from hotrain.parts import arch_half, keystone
    D = replace(P, run_style="deck_truss")
    b = 16 * INCH
    part = arch_half.make(replace(D, rivet_d=0.0, pier_relief=0.0), b)
    h, z = L.half_len(b), keystone.key_z(D) + D.pier_depth
    probe = Pos(h - 0.06, z - 10, 0.5) * Box(0.05, 20, 1, align=(Align.MIN,) * 3)
    pieces = sorted((s.bounding_box() for s in (part & probe).solids()), key=lambda bb: bb.min.Y)
    gap = pieces[1].min.Y - pieces[0].max.Y
    k = keystone.key_params(D)
    assert gap == pytest.approx(k.key_waist + 2 * D.fit_key, abs=0.05)



@pytest.mark.slow
def test_bambu_prints_every_rivet_size(tmp_path):
    """Bambu drops what it can't extrude; every strip's head layers must carry extrusions over that strip."""
    import re
    import zipfile
    from cadkit import slicers
    from hotrain import build
    from hotrain.plates import Plate
    s = slicers.active()
    if not s.available() or s.name != "bambu":
        pytest.skip("needs Bambu Studio")
    build.write_plates([Plate("fit_test", 1, [("fit_test", fit_test.make(P))])], tmp_path, tmp_path / "p.csv", p=P)
    s.slice_report(tmp_path / "fit_test.3mf", tmp_path / "s.3mf")
    tops = {round(P.panel_t + P.printer.layer * (k + 1), 2) for k in range(round(P.printer.layers(P.rivet_h) / P.printer.layer))}
    x = y = 0.0
    z, hits = None, {}
    for ln in zipfile.ZipFile(tmp_path / "s.3mf").read("Metadata/plate_1.gcode").decode().splitlines():
        if ln.startswith("; Z_HEIGHT:"):
            z = round(float(ln.split(":")[1]), 2)
        if re.match(r"^G[0-3] ", ln):
            d = dict((k, float(v)) for k, v in re.findall(r"([XYE])([-\d.]+)", ln.split(";")[0]))
            x, y = d.get("X", x), d.get("Y", y)
            if d.get("E", 0) > 0 and z in tops:
                for i in range(len(fit_test.RIVET_SIZES)):  # strips sit at (150, 40 + 15 i), RIVET_STRIP in size
                    if 150 <= x <= 150 + fit_test.RIVET_STRIP[0] and 40 + 15 * i <= y <= 40 + 15 * i + fit_test.RIVET_STRIP[1]:
                        hits[(i, z)] = hits.get((i, z), 0) + 1
    heads = 2 * fit_test.rivet_count(P)
    assert all(hits.get((i, z), 0) >= heads for i in range(len(fit_test.RIVET_SIZES)) for z in tops), hits
