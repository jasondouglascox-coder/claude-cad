"""The machine parts are checked against and packed for."""
from dataclasses import dataclass

class _Unset:
    def __repr__(self):
        return "<from settings>"


_UNSET = _Unset()  # "not passed": filled from settings


@dataclass(frozen=True)
class Printer:
    """Anything not passed comes from cadkit.settings (your CADKIT_* variables or cadkit.toml); with nothing set, a
    Bambu Lab A1: 256 x 256 mm, 0.4 mm nozzle, 0.2 mm layers. A bed passed alone is square; pass bed_y too for a
    rectangular one."""
    bed: float = _UNSET  # bed width (X), mm
    margin: float = _UNSET  # kept clear across the bed (half on each edge)
    layer: float = _UNSET  # tops, color seams and inlays belong on multiples of this
    nozzle: float = _UNSET  # walls thinner than this don't print
    first_layer: float | None = _UNSET  # Bambu's 0.16 mm profiles print a 0.2 mm first layer; None = same as layer
    bed_y: float | None = _UNSET  # bed depth (Y), mm; None = square

    def __post_init__(self):
        names = ("bed", "margin", "layer", "nozzle", "first_layer", "bed_y")
        if all(getattr(self, n) is not _UNSET for n in names):
            return
        from cadkit.settings import settings
        s = settings()
        bed_given = self.bed is not _UNSET
        for n, v in (("bed", s.bed_x), ("margin", s.margin), ("layer", s.layer), ("nozzle", s.nozzle),
                     ("first_layer", s.first_layer)):
            if getattr(self, n) is _UNSET:
                object.__setattr__(self, n, v)
        if self.bed_y is _UNSET:
            object.__setattr__(self, "bed_y", None if bed_given or s.bed_y == s.bed_x else s.bed_y)

    @property
    def first(self) -> float:
        return self.first_layer or self.layer

    def on_layer(self, z: float, tol: float = 1e-6) -> bool:
        """True when z is a layer boundary: 0, first, first + layer, first + 2 layer, ..."""
        if abs(z) < tol:
            return True
        k = (z - self.first) / self.layer
        return k > -tol and abs(k - round(k)) < tol

    def snap(self, z: float) -> float:
        """The layer boundary nearest z (at least the first layer): for heights that must print whole, like a part's
        thickness or a color seam, so a design follows the user's layer height."""
        k = max(round((z - self.first) / self.layer), 0)
        return round(self.first + k * self.layer, 6)

    def layers(self, t: float) -> float:
        """A thickness stacked on a layer boundary, rounded to whole layers (at least one): a raised mark, a collar
        above a floor. Its top lands on a boundary too."""
        return round(max(round(t / self.layer), 1) * self.layer, 6)

    @property
    def usable_x(self) -> float:
        return self.bed - self.margin

    @property
    def usable_y(self) -> float:
        return (self.bed_y or self.bed) - self.margin

    @property
    def usable(self) -> float:
        """The usable square: the shorter side."""
        return min(self.usable_x, self.usable_y)


A1 = Printer(bed=256.0, margin=5.0, layer=0.2, nozzle=0.4, first_layer=None, bed_y=None)


def default() -> Printer:
    """The printer from your settings."""
    from cadkit.settings import settings
    return settings().printer()
