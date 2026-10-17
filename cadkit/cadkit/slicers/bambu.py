"""Bambu Studio: project 3MF that opens colored, checked through its command line (cadkit.bambu)."""
import json
from pathlib import Path

from cadkit import bambu
from cadkit.slicers import Slicer, Unavailable, register


@register
class BambuStudio(Slicer):
    name, label = "bambu", "Bambu Studio"

    def find(self) -> Path | None:
        return bambu.find()

    def tower_keepout(self, settings: Path | None = None, pad: float = 3.0) -> tuple[float, float, float, float] | None:
        """The prime tower's corner from the project settings: it prints from (wipe_tower_x, wipe_tower_y) less its
        brim, about prime_tower_width square (measured: x 34.5-74.2, y 212.9-252.1 on the A1 template, at 0.2 and
        0.08 mm layers), plus pad mm. Bambu refuses to slice a plate with a part in it ("gcode path conflicts")."""
        from cadkit.settings import settings as cfg
        conf = json.loads(Path(settings or cfg().slicer_settings or self.default_settings()).read_text())
        if str(conf.get("enable_prime_tower", "1")) != "1":
            return None
        first = lambda v: float(v[0] if isinstance(v, list) else v)
        x, y = first(conf["wipe_tower_x"]), first(conf["wipe_tower_y"])
        w, brim = first(conf["prime_tower_width"]), first(conf.get("prime_tower_brim_width", 3))
        return x - brim - pad, y - brim - pad, x + w + brim + pad, y + w + brim + pad

    def roundtrip(self, src: Path, dst: Path | None = None) -> Path:
        if not self.available():
            raise Unavailable("bambu: Bambu Studio not found; set CADKIT_SLICER_PATH (or BAMBU_STUDIO)")
        return bambu.roundtrip(src, dst)

    def slice_report(self, src: Path, dst: Path | None = None) -> dict:
        if not self.available():
            raise Unavailable("bambu: Bambu Studio not found; set CADKIT_SLICER_PATH (or BAMBU_STUDIO)")
        return bambu.slice_report(src, dst)

    def slice_all(self, src: Path, dst: Path | None = None) -> list[dict]:
        if not self.available():
            raise Unavailable("bambu: Bambu Studio not found; set CADKIT_SLICER_PATH (or BAMBU_STUDIO)")
        return bambu.slice_all(src, dst)
