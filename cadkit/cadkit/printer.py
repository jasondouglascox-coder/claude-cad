"""The machine parts are checked against and packed for."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Printer:
    """Defaults: Bambu Lab A1, 0.4 mm nozzle, 0.2 mm layers."""
    bed: float = 256.0  # square bed side, mm
    margin: float = 5.0  # kept clear across the bed (half on each edge)
    layer: float = 0.2  # tops, color seams and inlays belong on multiples of this
    nozzle: float = 0.4  # walls thinner than this don't print

    @property
    def usable(self) -> float:
        return self.bed - self.margin


A1 = Printer()
