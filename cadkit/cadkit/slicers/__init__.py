"""Slicers behind one small interface, so plates and slicer checks work with whatever you print with.

Pick one with CADKIT_SLICER (or [slicer] name in cadkit.toml): `bambu` (the default, Bambu Studio) or `none`
(write plates, skip slicer checks). Projects call `active()`; tests skip slicer checks when it isn't available().

Adding PrusaSlicer, Cura, OrcaSlicer...: subclass `Slicer` in a module here, decorate it with `@register`, import it
at the bottom of this file, and run cadkit/tests/test_slicers.py. See CONTRIBUTING.md.
"""
from pathlib import Path

from build123d import Shape

from cadkit import bambu3mf

# objects for a project file: (object name, [(part name, shape, filament number from 1)])
Objects = list[tuple[str, list[tuple[str, Shape, int]]]]


class Unavailable(RuntimeError):
    """The slicer isn't installed (or can't do this)."""


class Slicer:
    """What cadkit needs from a slicer. The defaults write a 3MF any slicer loads (Bambu's project format: geometry
    everywhere, a filament per part in Bambu Studio and OrcaSlicer) and can't run anything."""
    name = ""
    label = ""  # what people call it
    project_suffix = ".3mf"

    def find(self) -> Path | None:
        """The slicer's executable, or None when it isn't installed."""
        return None

    def available(self) -> bool:
        return self.find() is not None

    def default_settings(self) -> Path | None:
        """Project-settings template for write_project when the project passes none."""
        return bambu3mf.SETTINGS

    def write_project(self, path: Path, objects: Objects, settings: Path | None = None) -> Path:
        """A project file that opens with each part on its filament. Override to write your slicer's own format."""
        from cadkit.settings import settings as cfg
        bambu3mf.write(path, objects, settings or cfg().slicer_settings or self.default_settings())
        return Path(path)

    def read_filaments(self, path: Path) -> list[tuple[str, int, dict]]:
        """[(object, its filament, {part: filament})], read back from a project file this slicer wrote or saved."""
        return bambu3mf.read_filaments(path)

    def same_objects(self, a: Path, b: Path, tol: float = 0.01) -> bool:
        """Same objects with the same meshes (within tol mm), in any order."""
        return bambu3mf.same_objects(a, b, tol)

    def roundtrip(self, src: Path, dst: Path | None = None) -> Path:
        """Have the slicer load src and save it back: what it didn't understand comes back different."""
        raise Unavailable(f"{self.name}: can't load and save files (not installed, or not implemented)")

    def slice_report(self, src: Path, dst: Path | None = None) -> dict:
        """Slice plate 1: {"grams": {filament: g}, "layers": [(filaments, first layer, last layer)]}, filaments from 1."""
        raise Unavailable(f"{self.name}: can't slice (not installed, or not implemented)")


SLICERS: dict[str, type[Slicer]] = {}


def register(cls: type[Slicer]) -> type[Slicer]:
    SLICERS[cls.name] = cls
    return cls


def get(name: str) -> Slicer:
    try:
        return SLICERS[name]()
    except KeyError:
        raise ValueError(f"unknown slicer {name!r}; known: {', '.join(sorted(SLICERS))}. To add yours, see "
                         f"CONTRIBUTING.md ('Adding a slicer')") from None


def active() -> Slicer:
    """The slicer from your settings (CADKIT_SLICER; default bambu)."""
    from cadkit.settings import settings
    return get(settings().slicer)


@register
class NoSlicer(Slicer):
    name, label = "none", "no slicer (plates only)"


from cadkit.slicers import bambu  # noqa: E402,F401  (registers "bambu")
