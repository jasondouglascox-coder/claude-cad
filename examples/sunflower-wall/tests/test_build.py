"""The build writes the plate (a project that opens colored), the painted STEP and the renders."""
import pytest

from cadkit import slicers
from cadkit.settings import settings
from sunflower import build, flower

S = flower.params()


@pytest.mark.slow
def test_build_writes_the_plate_step_and_renders(tmp_path):
    assert build.main(["all", "--out", str(tmp_path)]) == 0
    s, f = slicers.active(), settings().filament
    plate = tmp_path / "plates" / f"{build.NAME}{s.project_suffix}"
    assert s.read_filaments(plate) == [(build.NAME, f(S.slot_petals), {
        "flower_yellow": f(S.slot_petals), "flower_orange": f(S.slot_beads), "flower_black": f(S.slot_center),
        "flower_brown": f(S.slot_seeds)})]
    assert (tmp_path / f"{build.NAME}.step").exists() and (tmp_path / "plates.csv").exists()
    for name in ("front", "iso", "side"):
        assert (tmp_path / "render" / f"{name}.png").exists()
