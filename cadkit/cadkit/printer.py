"""The machine parts are checked against and packed for."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Printer:
    """Defaults: Bambu Lab A1, 0.4 mm nozzle, 0.2 mm layers."""
    bed: float = 256.0  # square bed side, mm
    margin: float = 5.0  # kept clear across the bed (half on each edge)
    layer: float = 0.2  # tops, color seams and inlays belong on multiples of this
    nozzle: float = 0.4  # walls thinner than this don't print
    first_layer: float | None = None  # Bambu's 0.16 mm profiles print a 0.2 mm first layer; None = same as layer

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
    def usable(self) -> float:
        return self.bed - self.margin


A1 = Printer()
