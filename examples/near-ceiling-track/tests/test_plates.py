import itertools
from collections import Counter
from dataclasses import replace

import pytest

from hotrain import layout as L
from hotrain import plates
from hotrain.params import INCH, P


def test_nested_arch_pair_is_compact_with_clearance():
    pair = plates.nested_arch_pair(P, 16 * INCH)
    a, b = pair.solids()
    assert a.distance_to(b) >= plates.GAP - 0.05
    bb = pair.bounding_box()
    assert bb.size.Y < 2 * (P.pier_depth + P.tie_h) - 30  # really nests, not just stacked
    assert bb.min.Z == pytest.approx(0, abs=1e-6)


def check_plate(plate):
    shapes = [s for _, s in plate]
    for s in shapes:
        bb = s.bounding_box()
        assert bb.min.Z == pytest.approx(0, abs=1e-6)
        assert bb.min.X >= 0 and bb.min.Y >= 0 and bb.max.X <= P.bed and bb.max.Y <= P.bed_y
    for a, b in itertools.combinations(shapes, 2):
        ba, bb = a.bounding_box(), b.bounding_box()
        apart = (ba.max.X + plates.GAP <= bb.min.X or bb.max.X + plates.GAP <= ba.min.X
                 or ba.max.Y + plates.GAP <= bb.min.Y or bb.max.Y + plates.GAP <= ba.min.Y)
        assert apart or a.distance_to(b) >= plates.GAP - 0.05


@pytest.mark.slow
@pytest.mark.parametrize("bays", [[16 * INCH], [P.min_bay_len, P.max_bay_len]])
def test_every_plate_valid_and_every_part_printed(bays):
    from hotrain import build
    expected = Counter()
    for name, _, qty, _ in build.part_list(P, bays):
        expected[name] += qty
    got = Counter()
    for pl in plates.plates(P, bays):
        check_plate(pl.items)
        for name, _ in pl.items:
            got[name.split("#")[0]] += pl.qty
    assert got == expected


def test_standard_bay_kits_and_pooled_ladders():
    """Per-bay kits are single-color and dedupe across bays; all tie ladders share "ladders" plates."""
    one = plates.plates(P, [16 * INCH])
    gray = [pl for pl in one if not pl.name.startswith("ladders")]
    lad = [pl for pl in one if pl.name.startswith("ladders")]
    assert len(gray) == 3  # half span A, half span B (+ bracket), run ends
    assert all(not plates.is_two_color(s) for pl in gray for _, s in pl.items)
    n_lad = len(L.segments(P, [16 * INCH]))
    assert sum(len(pl.items) for pl in lad) == n_lad and len(lad) == 1
    many = plates.plates(P, [16 * INCH] * 6)
    gray = [pl for pl in many if not pl.name.startswith("ladders")]
    assert len(gray) <= 4
    assert sum(pl.qty for pl in gray) == 2 * 6 + 1
    lad = [pl for pl in many if pl.name.startswith("ladders")]
    assert sum(len(pl.items) for pl in lad) == len(L.segments(P, [16 * INCH] * 6))
    assert len(lad) <= (len(L.segments(P, [16 * INCH] * 6)) + 2) // 3  # at least ~3 ladders per plate


@pytest.mark.slow
def test_corner_plates_valid_and_complete():
    from hotrain import corner_layout as CL
    pls = plates.corner_plates(P)
    for pl in pls:
        check_plate(pl.items)
    for corner in (CL.inside_corner(), CL.bridge_corner()):
        expected = Counter(n for n, _ in plates.corner_kit(P, corner))
        got = Counter()
        for pl in pls:
            if pl.name.startswith(corner.name):
                got.update(n for n, _ in pl.items)
        assert got == expected
    assert any(pl.name == "rod_jig" for pl in pls)


@pytest.mark.slow
def test_corner_plates_keep_pla_off_petg_and_swap_at_most_once():
    """The white PLA ceiling cleats print on their own bed: PLA and PETG want different temperatures, and white
    beside gray in the same layers would swap filament every layer."""
    from cadkit.plates import color_changes, is_multi_color
    from hotrain.build import filament
    for pl in plates.corner_plates(P):
        labels = [b.label for _, s in pl.items for b in (s.children if is_multi_color(s) else [s])]
        names = [n for n, s in pl.items if not is_multi_color(s)] + [l for l in labels if l.endswith(("_wood", "_steel"))]
        fils = {filament(P, n) for n in names}
        assert P.filament_white not in fils or fils == {P.filament_white}, pl.name
        assert color_changes(pl.items, P.printer, key=lambda n, b: filament(P, n)) <= 1, pl.name


@pytest.mark.slow
def test_every_two_color_plate_slices(tmp_path):
    """Bambu slices every brown/gray plate (runs, corners, starter): nothing on the bed where its prime tower
    prints. Before cadkit kept that corner free, all five failed with "gcode path conflicts"."""
    from concurrent.futures import ThreadPoolExecutor
    from cadkit import slicers
    from cadkit.plates import is_multi_color
    from hotrain import build
    s = slicers.active()
    if not s.available():
        pytest.skip("no slicer installed (settings: slicer)")
    D = replace(P, run_style="deck_truss")
    pls = plates.plates(D) + plates.corner_plates(D) + plates.all_in_one(D, [16 * INCH])
    two = [pl for pl in pls if any(is_multi_color(sh) for _, sh in pl.items)]
    assert len(two) >= 6
    build.write_plates(two, tmp_path, tmp_path / "p.csv", p=D)

    def layers(pl):
        return [f for f, _, _ in s.slice_report(tmp_path / f"{pl.name}{s.project_suffix}")["layers"]]

    with ThreadPoolExecutor(8) as ex:  # Bambu runs one process per plate: the laptop has the cores
        got = dict(zip((pl.name for pl in two), ex.map(layers, two)))
    assert all(v == [(D.filament_brown,), (D.filament_gray,)] for v in got.values()), got


def test_stragglers_share_plates():
    """A kit that overflows its plate (the riveted deck truss pair is deeper) sends the overflow to shared extras
    plates, like the pooled ladders, instead of a plate of one cross-frame per bay."""
    D = replace(P, run_style="deck_truss")
    bays = [418.2] * 3  # the room's bay length
    pls = plates.plates(D, bays)
    assert not [pl.name for pl in pls if pl.name.startswith("bay_") and pl.name.endswith("_2")]
    extras = [pl for pl in pls if pl.name.startswith("extras")]
    assert sum(pl.qty for pl in extras) == 1
    printed = Counter(n.split("#")[0] for pl in pls for n, _ in pl.items for _ in range(pl.qty))
    assert sum(q for n, q in printed.items() if n.startswith("cross_frame")) == 3 * 2 * len(L.post_us(D, 418.2))
