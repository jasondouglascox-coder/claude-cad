"""Your setup: printer, colors, slicer and projects folder, without editing cadkit.

Read in this order, later wins: built-in defaults (a Bambu A1 with an AMS lite and Bambu Studio), then a config
file, then environment variables. The config file is $CADKIT_CONFIG if set, else `cadkit.toml` at the repo root
(gitignored, so `git pull` never conflicts), else ~/.config/cadkit/cadkit.toml. `cadkit.toml.example` lists every
key. See what's in effect, and where each value came from:

    uv run python -m cadkit.settings
"""
import functools
import os
import sys
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# (config file section, key) -> (field, environment variable)
KEYS = {
    ("printer", "bed_x"): ("bed_x", "CADKIT_BED_X"),
    ("printer", "bed_y"): ("bed_y", "CADKIT_BED_Y"),
    ("printer", "margin"): ("margin", "CADKIT_MARGIN"),
    ("printer", "layer"): ("layer", "CADKIT_LAYER"),
    ("printer", "first_layer"): ("first_layer", "CADKIT_FIRST_LAYER"),
    ("printer", "nozzle"): ("nozzle", "CADKIT_NOZZLE"),
    ("colors", "count"): ("colors", "CADKIT_COLORS"),
    ("colors", "changes"): ("color_changes", "CADKIT_COLOR_CHANGES"),
    ("slicer", "name"): ("slicer", "CADKIT_SLICER"),
    ("slicer", "path"): ("slicer_path", "CADKIT_SLICER_PATH"),
    ("slicer", "settings"): ("slicer_settings", "CADKIT_SLICER_SETTINGS"),
    ("projects", "dir"): ("projects", "CADKIT_PROJECTS"),
}
BED = (("printer", "bed"), "CADKIT_BED")  # one value for a square bed
PATHS = {"slicer_path", "slicer_settings", "projects"}


@dataclass(frozen=True)
class Settings:
    bed_x: float = 256.0  # mm
    bed_y: float = 256.0
    margin: float = 5.0  # kept clear across the bed (half on each edge)
    layer: float = 0.2
    first_layer: float | None = None  # None = same as layer
    nozzle: float = 0.4
    colors: int = 4  # filaments one print can use: 4 with an AMS lite, 1 without
    color_changes: int = 1  # color changes per plate before the build warns
    slicer: str = "bambu"  # a name in cadkit.slicers.SLICERS, or "none"
    slicer_path: Path | None = None  # the slicer's executable; None = where it usually installs
    slicer_settings: Path | None = None  # the slicer's project-settings template; None = the built-in one
    projects: Path = REPO / "examples"  # where cadkit.new puts new projects
    sources: dict = field(default_factory=dict, compare=False)  # field -> "default", a file, or an env var

    def filament(self, n: int) -> int:
        """The filament a body meant for filament n prints with here: n, or 1 on a one-color printer."""
        return 1 if self.colors == 1 else n

    def printer(self):
        from cadkit.printer import Printer
        return Printer(bed=self.bed_x, bed_y=None if self.bed_y == self.bed_x else self.bed_y, margin=self.margin,
                       layer=self.layer, nozzle=self.nozzle, first_layer=self.first_layer)


def candidates(env) -> list[Path]:
    if env.get("CADKIT_CONFIG"):
        return [Path(env["CADKIT_CONFIG"]).expanduser()]
    return [REPO / "cadkit.toml", Path.home() / ".config" / "cadkit" / "cadkit.toml"]


def _convert(name: str, raw, where: str, base: Path):
    kind = {f.name: f.type for f in fields(Settings)}[name]
    try:
        if name in PATHS:
            p = Path(str(raw)).expanduser()
            return p if p.is_absolute() else base / p
        if name in ("colors", "color_changes"):
            v = int(raw)
            if v < (1 if name == "colors" else 0):
                raise ValueError(f"{v} is too small")
            return v
        if name == "slicer":
            return str(raw).strip().lower()
        v = float(raw)
        if v <= 0:
            raise ValueError(f"{v} must be positive")
        return v
    except (TypeError, ValueError) as e:
        raise ValueError(f"{where}: bad {name} {raw!r} ({kind}): {e}") from None


def load(env=None, files=None) -> Settings:
    """Settings from the first config file that exists (default: `candidates`) and the environment."""
    env = os.environ if env is None else env
    files = candidates(env) if files is None else files
    vals = {f.name: f.default for f in fields(Settings) if f.name != "sources"}
    src = dict.fromkeys(vals, "default")

    def put(name, raw, where, base):
        vals[name], src[name] = _convert(name, raw, where, base), where

    for f in files:
        f = Path(f)
        if not f.is_file():
            continue
        data = tomllib.loads(f.read_text())
        for section, table in data.items():
            if not isinstance(table, dict):
                raise ValueError(f"{f}: {section!r} must be a [section]")
            for key, raw in table.items():
                if (section, key) == BED[0]:
                    put("bed_x", raw, str(f), f.parent)
                    put("bed_y", raw, str(f), f.parent)
                elif (section, key) in KEYS:
                    put(KEYS[section, key][0], raw, str(f), f.parent)
                else:
                    known = ", ".join(f"[{s}] {k}" for s, k in [*KEYS, BED[0]])
                    raise ValueError(f"{f}: unknown setting [{section}] {key}; known: {known}")
        break
    if env.get(BED[1]):
        put("bed_x", env[BED[1]], BED[1], Path.cwd())
        put("bed_y", env[BED[1]], BED[1], Path.cwd())
    for name, var in KEYS.values():
        if env.get(var):
            put(name, env[var], var, Path.cwd())
    return Settings(**vals, sources=src)


@functools.cache
def settings() -> Settings:
    """The settings in effect (read once; `reload()` after changing the environment)."""
    return load()


def reload() -> Settings:
    settings.cache_clear()
    return settings()


def describe(s: Settings) -> str:
    rows = [(f.name, getattr(s, f.name), s.sources.get(f.name, "default")) for f in fields(Settings)
            if f.name != "sources"]
    w = max(len(n) for n, _, _ in rows)
    return "\n".join(f"{n:<{w}}  {v!s:<40}  {where}" for n, v, where in rows)


if __name__ == "__main__":
    s = settings()
    print(describe(s))
    found = [str(f) for f in candidates(os.environ) if Path(f).is_file()]
    print(f"\nconfig file: {found[0] if found else 'none (looked in ' + ', '.join(map(str, candidates(os.environ))) + ')'}")
    sys.exit(0)
