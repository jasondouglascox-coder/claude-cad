"""The whole flower: nothing overlaps (pins in slots, petals under the head, screw in the keyhole), and it can fail."""
import pytest
from build123d import Align, Box, Pos

from cadkit.clash import find_clashes
from sunflower import assembly
from sunflower.params import P, Params


@pytest.fixture(scope="module")
def parts():
    return assembly.placed_parts(P)


def test_nothing_overlaps_including_wall_and_screw(parts):
    env = assembly.environment(P)
    assert find_clashes(parts + env) == []


def test_parts_count(parts):
    names = [n for n, _ in parts]
    assert sum(n.startswith("back") for n in names) == 4 and sum(n.startswith("front") for n in names) == 4
    assert sum(n.startswith("pin") for n in names) == 8
    assert sum(n.startswith("center") for n in names) == 2


def test_rings_stack_flush(parts):
    d = dict(parts)
    assert d["front_0"].bounding_box().min.Z == pytest.approx(P.back_t)
    assert d["center_black"].bounding_box().min.Z == pytest.approx(P.back_t + P.front_t)
    assert d["pin_0"].bounding_box().min.Z == pytest.approx(0)  # head flush with the wall


def test_neighbouring_quarters_keep_the_seam_gap(parts):
    d = dict(parts)
    for layer in ("back", "front"):
        for q in range(4):
            gap = d[f"{layer}_{q}"].distance_to(d[f"{layer}_{(q + 1) % 4}"])
            assert gap >= P.seam_gap - 1e-3


@pytest.mark.slow
def test_too_tight_pins_clash():
    tight = Params(fit=-0.4)
    clashes = find_clashes(assembly.placed_parts(tight))
    assert any(a.startswith("pin") or b.startswith("pin") for a, b, _ in clashes)
