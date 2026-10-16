"""Every example shows what it makes: pictures at the top of its README, files that exist."""
import re

import pytest

from cadkit.settings import REPO

EXAMPLES = sorted(p for p in (REPO / "examples").iterdir() if (p / "pyproject.toml").exists())


@pytest.mark.parametrize("ex", EXAMPLES, ids=lambda p: p.name)
def test_readme_shows_pictures_that_exist(ex):
    readme = (ex / "README.md").read_text()
    srcs = re.findall(r'<img src="([^"]+)"', readme) + re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
    assert srcs, f"{ex.name}/README.md shows no pictures: render with its build, copy to docs/images/"
    for s in srcs:
        assert (ex / s).is_file(), f"{ex.name}: {s} is missing"
    first = readme.find(srcs[0])
    assert first < len(readme) // 3, f"{ex.name}: put the first picture near the top"
