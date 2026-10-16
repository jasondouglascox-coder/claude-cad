"""cadkit.new: a new project from the fit-coupon template, in your projects folder (settings: projects)."""
import tomllib

import pytest

from cadkit import new
from cadkit.settings import REPO


def test_new_project_is_the_template_renamed(tmp_path):
    d = new.create("router-bracket", tmp_path)
    assert d == tmp_path / "router-bracket"
    assert (d / "router_bracket" / "params.py").exists() and not (d / "fitcoupon").exists()
    for f in d.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".toml", ".md"):
            assert "fitcoupon" not in f.read_text(), f
    proj = tomllib.loads((d / "pyproject.toml").read_text())
    assert proj["project"]["name"] == "router-bracket"
    src = proj["tool"]["uv"]["sources"]["cadkit"]["path"]
    assert (d / src).resolve() == (REPO / "cadkit").resolve()
    assert src == str((REPO / "cadkit").resolve())  # outside the repo: absolute, not ../../../..
    assert (d / "docs" / "specs").is_dir() and (d / "docs" / "images").is_dir()
    assert "# router-bracket" in (d / "README.md").read_text()
    assert not any(p.name in (".venv", "out", "uv.lock", "__pycache__") for p in d.rglob("*"))


def test_inside_the_repo_the_path_is_relative(tmp_path):
    import shutil
    d = new.create("zz-tmp-test", REPO / "out" / "test-new")  # gitignored; examples/ would race test_examples
    try:
        assert tomllib.loads((d / "pyproject.toml").read_text())["tool"]["uv"]["sources"]["cadkit"]["path"] \
            == "../../../cadkit"
    finally:
        shutil.rmtree(d)


def test_defaults_to_the_projects_folder(tmp_path, monkeypatch):
    from cadkit import settings
    monkeypatch.setenv("CADKIT_PROJECTS", str(tmp_path / "mine"))
    settings.reload()
    try:
        assert new.create("lamp") == tmp_path / "mine" / "lamp"
    finally:
        monkeypatch.undo()
        settings.reload()


def test_never_overwrites_and_wants_a_usable_name(tmp_path):
    new.create("lamp", tmp_path)
    with pytest.raises(FileExistsError):
        new.create("lamp", tmp_path)
    with pytest.raises(ValueError, match="name"):
        new.create("3d lamp!", tmp_path)
