"""Everything on the bar: clip, block, three markers and both tubes clash with nothing, at either length reading
and with worn felts; the felts reach the filament and nothing else does; the gantry's space stays empty."""
import pytest

from cadkit.clash import find_clashes
from sharpie_colorizer.assembly import filament, marker, placed_parts
from sharpie_colorizer.params import P

MARKERS = range(len(P.azimuths_deg))


@pytest.mark.parametrize("reading,wear", [("long", 0.0), ("short", 0.0), ("short", P.wear_max)],
                         ids=["long", "short", "worn"])
def test_markers_clear_block(reading, wear):
    """Review Focus 2 & 3."""
    assert find_clashes(placed_parts(P, reading, wear)) == []


def test_clash_test_can_fail():
    """Worn far past wear_max and pushed in, the nose and shoulder hit plastic."""
    assert find_clashes(placed_parts(P, "short", P.wear_max + 3.0)) != []


@pytest.mark.parametrize("i", MARKERS)
@pytest.mark.parametrize("wear", [0.0, P.wear_max])
def test_felt_reaches_the_filament(i, wear):
    assert (marker(P, i, "long", wear) & filament(P)).volume > 0.01


@pytest.mark.parametrize("i", MARKERS)
def test_nose_never_touches_filament(i):
    """Review Focus 3: a worn marker pushed in touches the filament with felt only."""
    for reading in ("long", "short"):
        assert (marker(P, i, reading, P.wear_max, felt=False) & filament(P)).volume == pytest.approx(0, abs=1e-4)


def test_tube_paths_clear():
    """Review Focus 4: the tubes are in placed_parts; name them so a clash shows which."""
    names = [n for n, _ in placed_parts(P)]
    assert "inlet_tube" in names and "outlet_tube" in names
    assert [c for c in find_clashes(placed_parts(P)) if "tube" in c[0] or "tube" in c[1]] == []


def test_gantry_space_empty():
    floor = -P.bar_h / 2 - P.clip_clear - P.clip_t - 1e-3
    low = {n: s.bounding_box().min.Z for n, s in placed_parts(P) if n not in ("bar", "outlet_tube")}
    assert {n: z for n, z in low.items() if z < floor} == {}
