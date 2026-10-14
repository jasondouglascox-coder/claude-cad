import pytest
from hotrain.layout import (BAYS, validate_bays, bay_pitch, joint_u, post_us, rib_low, segments, tab_us, tab_xs,
                            ties, ties_per_bay, half_len, springing_u)
from hotrain.params import INCH, P


def test_rib_low_hits_pier_and_crown_depths():
    b = 16 * INCH
    assert rib_low(P, b, springing_u(P)) == pytest.approx(-P.pier_depth)
    assert rib_low(P, b, half_len(b)) == pytest.approx(-P.crown_depth)


@pytest.mark.parametrize("b", [12 * INCH, 16 * INCH, 19.5 * INCH, 17.3 * INCH])
def test_bay_pitch_close_to_nominal_and_whole(b):
    pb = bay_pitch(P, b)
    assert abs(pb - P.tie_pitch) < 0.2  # whole multiple of long_tie_every ties per bay
    assert ties_per_bay(P, b) % P.long_tie_every == 0
    assert ties_per_bay(P, b) * pb == pytest.approx(b)


@pytest.mark.parametrize("b", [12 * INCH, 16 * INCH, 19.5 * INCH, 17.3 * INCH])
def test_tabs_stay_clear_of_ladder_joint(b):
    uj = joint_u(P, b)
    assert tab_us(P, b), "every half needs at least one tab"
    for u in tab_us(P, b):
        assert abs(u - uj) >= P.tab_len / 2 + P.tab_joint_keepout


def test_default_bay_has_four_tabs_and_three_posts_per_half():
    assert tab_us(P, 16 * INCH) == pytest.approx([25.4, 76.2, 127.0, 177.8])
    assert post_us(P, 16 * INCH) == pytest.approx([50.8, 101.6, 152.4])


@pytest.mark.parametrize("bays", [[16 * INCH], [16 * INCH, 14 * INCH, 19.5 * INCH]])
def test_segments_fit_bed_and_chain(bays):
    segs = segments(P, bays)
    assert not segs[0].female_start and not segs[-1].male_end
    for a, b in zip(segs, segs[1:]):
        assert a.x_end == b.x_start and a.male_end and b.female_start
    for s in segs:
        assert 0 < s.x_end - s.x_start <= P.bed_usable


@pytest.mark.parametrize("bays", [[16 * INCH], [16 * INCH, 14 * INCH, 19.5 * INCH]])
def test_no_tie_straddles_a_ladder_joint(bays):
    for s in segments(P, bays)[1:]:
        for t in ties(P, bays):
            assert abs(t.x - s.x_start) >= P.tie_w / 2 + 0.5


def test_ties_cover_end_piers():
    ts = ties(P, BAYS)
    assert ts[0].x - P.tie_w / 2 >= -P.pier_w / 2
    assert ts[0].x < -P.pier_w / 2 + 5
    assert ts[-1].x + P.tie_w / 2 <= sum(BAYS) + P.pier_w / 2


def test_tab_xs_mirror_within_bay():
    xs = tab_xs(P, BAYS)
    b = BAYS[0]
    assert xs == pytest.approx(sorted(b - x for x in xs))


@pytest.mark.parametrize("bays", [[], [600.0], [16 * INCH, 100.0]])
def test_validate_bays_rejects_unprintable_runs(bays):
    with pytest.raises(ValueError):
        validate_bays(P, bays)


def test_validate_bays_accepts_range_ends():
    validate_bays(P, [P.min_bay_len, P.max_bay_len, 16 * INCH])


@pytest.mark.parametrize("bays", [[P.max_bay_len, P.max_bay_len, P.max_bay_len], [P.min_bay_len, P.max_bay_len]])
def test_segments_including_jigsaw_fit_bed(bays):
    for s in segments(P, bays):
        assert s.x_end - s.x_start + (P.jig_len if s.male_end else 0) <= P.bed_usable


@pytest.mark.parametrize("b", [P.min_bay_len, 16 * INCH, P.max_bay_len])
def test_cross_frame_notch_walls_both_sides(b):
    from hotrain.layout import cf_depth, rib_low
    nw = (P.cf_t + P.fit_slide) / 2
    for u in post_us(P, b):
        top = -cf_depth(P, b, u) + P.rib_notch
        assert min(top - rib_low(P, b, u - nw), top - rib_low(P, b, u + nw)) >= P.rib_notch - 1e-9


@pytest.mark.parametrize("bays", [[16 * INCH, 16 * INCH, 16 * INCH], [16 * INCH] * 2 + [14 * INCH]])
def test_handrail_posts_evenly_spaced_across_whole_run(bays):
    xs = [t.x for t in ties(P, bays) if t.long]
    gaps = [b - a for a, b in zip(xs, xs[1:])]
    n_equal = sum(1 for g in gaps if abs(g - gaps[0]) < 0.01)
    if len(set(bays)) == 1:
        assert max(gaps) - min(gaps) < 0.01  # seamless, piers included
    assert min(gaps) > 3.5 * P.tie_pitch and max(gaps) < 4.5 * P.tie_pitch


@pytest.mark.parametrize("bays", [[16 * INCH], [P.min_bay_len, 17.3 * INCH, P.max_bay_len], [P.max_bay_len] * 3])
def test_handrail_pieces_start_on_a_post_and_fit_bed(bays):
    from hotrain.layout import handrail_pieces
    pieces = handrail_pieces(P, bays)
    posts = [t.x for t in ties(P, bays) if t.long]
    assert sorted(x for pc in pieces for x in pc.posts) == pytest.approx(posts)  # every post owned once
    for a, b in zip(pieces, pieces[1:]):
        assert a.x_end == pytest.approx(b.posts[0] - P.handrail_post_w / 2 - P.handrail_gap)  # bars butt next post
    for pc in pieces:
        assert pc.x_start == pytest.approx(pc.posts[0] - P.handrail_post_w / 2)
        assert pc.x_end - pc.x_start <= P.bed_usable


def test_corner_ends_stop_at_the_anchor():
    from hotrain.layout import CORNER, FREE, run_extent
    b = [16 * INCH]
    assert run_extent(P, b, (CORNER, CORNER)) == (0.0, b[0])
    assert run_extent(P, b, (FREE, FREE)) == (-P.pier_w / 2, b[0] + P.pier_w / 2)
    ts = ties(P, b, (CORNER, CORNER))
    assert ts[0].x > 0 and ts[-1].x < b[0]
