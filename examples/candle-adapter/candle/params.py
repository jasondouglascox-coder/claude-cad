"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these."""
from dataclasses import dataclass

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    base_d: float = 37.0  # disc that sits inside the chandelier cup's lip and gets hot-glued
    base_t: float = 3.0  # also the floor under the candle; a layer multiple
    candle_d: float = 20.0  # the hole the candle stands in
    depth: float = 15.0  # how far the candle sits in, top of collar to floor
    wall: float = 3.0  # collar wall around the candle
    root_fillet: float = 2.0  # collar-to-disc fillet, for strength (concave, faces up: prints fine)
    mouth_chamfer: float = 0.8  # lead-in at the top of the hole
    filament_black: int = 3  # AMS slot
    printer: Printer = Printer()

    @property
    def collar_d(self) -> float:
        return self.candle_d + 2 * self.wall

    @property
    def height(self) -> float:
        return self.base_t + self.depth


P = Params()
