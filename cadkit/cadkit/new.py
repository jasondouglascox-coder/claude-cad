"""Start a project from the template (examples/fit-coupon) in your projects folder.

    uv run --project cadkit python -m cadkit.new router-bracket        # into settings `projects` (CADKIT_PROJECTS)
    uv run --project cadkit python -m cadkit.new router-bracket --dir ~/prints

The copy keeps the template's layout (params, parts, build with plates and renders, tests), renames the package,
and points its cadkit dependency at this checkout, so it works from any folder, tracked by git or not.
"""
import argparse
import os
import re
import shutil
import sys
from pathlib import Path

from cadkit.settings import REPO, settings

TEMPLATE = REPO / "examples" / "fit-coupon"
SKIP = {".venv", "out", "uv.lock", "__pycache__", ".pytest_cache"}

README = """# {name}

Made with claude-cad from the fit-coupon template: replace the coupon in `{pkg}/parts.py` with your part.

<img src="docs/images/iso.png" width="49%" alt="{name}">

```bash
uv sync
uv run pytest                     # print checks, dimensions, the plate file, the slicer (if installed)
uv run python -m {pkg}.build      # out/plates (open in your slicer), out/step, out/render
```

The pictures in `docs/images/` are copies of `out/render/`; refresh them after a visible change.
Decisions go in `docs/specs/` (with an Amendments section), real-world measurements in `docs/measurements.md`.
"""


def create(name: str, folder: Path | None = None) -> Path:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name):
        raise ValueError(f"project name {name!r}: use letters, digits, - and _, starting with a letter")
    pkg = name.replace("-", "_").lower()
    dest = Path(folder or settings().projects).expanduser() / name
    if dest.exists():
        raise FileExistsError(f"{dest} already exists")
    shutil.copytree(TEMPLATE, dest, ignore=lambda d, names: [n for n in names if n in SKIP])
    (dest / "fitcoupon").rename(dest / pkg)
    for f in dest.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".toml", ".md"):
            f.write_text(f.read_text().replace("fitcoupon", pkg))
    cadkit = (REPO / "cadkit").resolve()
    inside = dest.resolve().is_relative_to(REPO.resolve())
    rel = os.path.relpath(cadkit, dest.resolve()) if inside else str(cadkit)  # relative only within this checkout
    toml = (dest / "pyproject.toml").read_text()
    toml = re.sub(r'(?m)^name = ".*"$', f'name = "{name}"', toml, count=1)
    toml = toml.replace('path = "../../cadkit"', f'path = "{rel}"')
    (dest / "pyproject.toml").write_text(toml)
    (dest / "README.md").write_text(README.format(name=name, pkg=pkg))
    for d in ("docs/specs", "docs/images"):
        (dest / d).mkdir(parents=True, exist_ok=True)
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cadkit.new", description=__doc__.splitlines()[0])
    ap.add_argument("name")
    ap.add_argument("--dir", help="parent folder (default: settings projects, CADKIT_PROJECTS)")
    a = ap.parse_args(argv)
    d = create(a.name, Path(a.dir) if a.dir else None)
    print(f"created {d}\nnext: cd {d} && uv sync && uv run pytest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
