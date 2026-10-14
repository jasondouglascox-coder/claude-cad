"""Outputs: a Bambu project 3MF with a filament per body, and (slow) what Bambu Studio makes of it."""
import pytest

from cadkit import bambu, bambu3mf
from grover import build
from grover.params import P


def test_build_writes_a_colored_bambu_plate(tmp_path):
    assert build.main(["3mf", "--out", str(tmp_path)]) == 0
    got = {n: parts for n, _, parts in bambu3mf.read_filaments(tmp_path / "plates" / "grover_keychain.3mf")}
    assert got["grover_keychain"] == {f"grover_{c}": f for c, f in P.filament}
    cfg = (tmp_path / "bambu_settings.config").read_text()
    assert f'"layer_height": "{P.printer.layer}"' in cfg


@pytest.mark.slow
@pytest.mark.skipif(bambu.find() is None, reason="Bambu Studio not installed")
def test_bambu_slices_it_into_the_expected_color_bands(tmp_path):
    build.main(["3mf", "--out", str(tmp_path)])
    src = tmp_path / "plates" / "grover_keychain.3mf"
    back = bambu.roundtrip(src, tmp_path / "rt.3mf")
    assert bambu3mf.object_sizes(back) == bambu3mf.object_sizes(src)
    report = bambu.slice_report(src, tmp_path / "s.3mf")
    fil = {c: f for c, f in P.filament}
    bands = [set(r[0]) for r in report["layers"]]
    assert bands[0] == {fil["brown"], fil["white"]}  # back inlay
    assert {fil["brown"]} in bands  # solid body
    assert {fil["white"], fil["orange"]} in bands  # base
    assert set(fil.values()) in bands  # face
    assert bands[-1] == {fil["white"], fil["brown"]}  # top
