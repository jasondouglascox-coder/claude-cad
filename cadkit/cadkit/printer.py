"""The machine parts are checked against and packed for."""
from dataclasses import dataclass, field


def _setting(name: str):
    def get():
        from cadkit.settings import settings
        s = settings()
        if name == "bed_y":
            return None if s.bed_y == s.bed_x else s.bed_y
        return getattr(s, name)
    return field(default_factory=get)


@dataclass(frozen=True)
class Printer:
    """Defaults come from cadkit.settings (your CADKIT_* variables or cadkit.toml); with nothing set, a Bambu Lab
    A1: 256 x 256 mm, 0.4 mm nozzle, 0.2 mm layers. For a rectangular bed pass bed_y too."""
    bed: float = _setting("bed_x")  # bed width (X), mm
    margin: float = _setting("margin")  # kept clear across the bed (half on each edge)
    layer: float = _setting("layer")  # tops, color seams and inlays belong on multiples of this
    nozzle: float = _setting("nozzle")  # walls thinner than this don't print
    first_layer: float | None = _setting("first_layer")  # Bambu's 0.16 mm profiles print a 0.2 mm first layer
    bed_y: float | None = _setting("bed_y")  # bed depth (Y), mm; None = square

    @property
    def first(self) -> float:
        return self.first_layer or self.layer

    def on_layer(self, z: float, tol: float = 1e-6) -> bool:
        """True when z is a layer boundary: 0, first, first + layer, first + 2 layer, ..."""
        if abs(z) < tol:
            return True
        k = (z - self.first) / self.layer
        return k > -tol and abs(k - round(k)) < tol

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
