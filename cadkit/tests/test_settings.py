"""Settings: built-in defaults (the A1 setup), then the config file, then environment variables."""
import pytest

from cadkit import settings as S
from cadkit.printer import A1, Printer


def write(tmp_path, text):
    f = tmp_path / "cadkit.toml"
    f.write_text(text)
    return f


def test_nothing_set_is_the_a1_setup():
    s = S.load(env={}, files=[])
    assert (s.bed_x, s.bed_y, s.margin, s.layer, s.nozzle) == (A1.bed, A1.bed, A1.margin, A1.layer, A1.nozzle)
    assert (s.colors, s.color_changes, s.slicer) == (4, 1, "bambu")
    assert s.projects == S.REPO / "examples"
    assert s.printer() == A1


def test_file_then_env(tmp_path):
    f = write(tmp_path, '[printer]\nbed_x = 250\nbed_y = 210\n[colors]\ncount = 1\n[slicer]\nname = "none"\n')
    s = S.load(env={}, files=[f])
    assert (s.bed_x, s.bed_y, s.colors, s.slicer) == (250, 210, 1, "none")
    assert s.sources["bed_y"] == str(f)
    s = S.load(env={"CADKIT_BED_Y": "200", "CADKIT_COLORS": "2"}, files=[f])
    assert (s.bed_x, s.bed_y, s.colors) == (250, 200, 2)
    assert s.sources["bed_y"] == "CADKIT_BED_Y"


def test_one_bed_value_means_square(tmp_path):
    assert (S.load(env={"CADKIT_BED": "220"}, files=[]).bed_x, S.load(env={"CADKIT_BED": "220"}, files=[]).bed_y) \
        == (220, 220)
    s = S.load(env={}, files=[write(tmp_path, "[printer]\nbed = 180\n")])
    assert (s.bed_x, s.bed_y) == (180, 180)


def test_first_existing_file_wins(tmp_path):
    a, b = tmp_path / "missing.toml", write(tmp_path, "[colors]\nchanges = 3\n")
    assert S.load(env={}, files=[a, b]).color_changes == 3
    assert S.load(env={"CADKIT_CONFIG": str(b)}).color_changes == 3


def test_relative_projects_dir_is_relative_to_the_file(tmp_path):
    s = S.load(env={}, files=[write(tmp_path, '[projects]\ndir = "my-prints"\n')])
    assert s.projects == tmp_path / "my-prints"


def test_typos_and_bad_values_say_where(tmp_path):
    with pytest.raises(ValueError, match="bed_xx"):
        S.load(env={}, files=[write(tmp_path, "[printer]\nbed_xx = 250\n")])
    with pytest.raises(ValueError, match="CADKIT_BED_X"):
        S.load(env={"CADKIT_BED_X": "wide"}, files=[])
    with pytest.raises(ValueError, match="CADKIT_COLORS"):
        S.load(env={"CADKIT_COLORS": "0"}, files=[])


def test_printer_defaults_follow_settings(monkeypatch):
    monkeypatch.setenv("CADKIT_BED_X", "250")
    monkeypatch.setenv("CADKIT_BED_Y", "210")
    monkeypatch.setenv("CADKIT_LAYER", "0.16")
    S.reload()
    try:
        p = Printer()
        assert (p.bed, p.bed_y, p.layer) == (250, 210, 0.16)
        assert Printer(bed=300).bed == 300  # explicit values still win
        assert A1.bed == 256  # the A1 stays the A1
    finally:
        monkeypatch.undo()
        S.reload()
    assert Printer() == A1


def test_rectangular_bed_has_two_usable_sides():
    p = Printer(bed=250, bed_y=210, margin=5)
    assert (p.usable_x, p.usable_y) == (245, 205)
    assert Printer(bed=256).usable_y == Printer(bed=256).usable_x == 251


def test_describe_lists_every_value_and_its_source():
    text = S.describe(S.load(env={"CADKIT_COLORS": "1"}, files=[]))
    assert "colors" in text and "CADKIT_COLORS" in text and "default" in text


def test_filament_for_this_setup():
    assert S.load(env={}, files=[]).filament(3) == 3
    assert S.load(env={"CADKIT_COLORS": "1"}, files=[]).filament(3) == 1


def test_example_file_lists_every_setting_and_parses_uncommented(tmp_path):
    text = (S.REPO / "cadkit.toml.example").read_text()
    for (section, key), (_, var) in S.KEYS.items():
        assert f"# {key} =" in text and var in text, key
    live = "\n".join(l[2:] if l.startswith("# ") and "=" in l.split("#")[1] else l for l in text.splitlines())
    s = S.load(env={}, files=[write(tmp_path, live)])
    assert s.bed_x == 256 and s.slicer == "bambu"
