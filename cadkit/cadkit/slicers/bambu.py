"""Bambu Studio: project 3MF that opens colored, checked through its command line (cadkit.bambu)."""
from pathlib import Path

from cadkit import bambu
from cadkit.slicers import Slicer, Unavailable, register


@register
class BambuStudio(Slicer):
    name, label = "bambu", "Bambu Studio"

    def find(self) -> Path | None:
        return bambu.find()

    def roundtrip(self, src: Path, dst: Path | None = None) -> Path:
        if not self.available():
            raise Unavailable("bambu: Bambu Studio not found; set CADKIT_SLICER_PATH (or BAMBU_STUDIO)")
        return bambu.roundtrip(src, dst)

    def slice_report(self, src: Path, dst: Path | None = None) -> dict:
        if not self.available():
            raise Unavailable("bambu: Bambu Studio not found; set CADKIT_SLICER_PATH (or BAMBU_STUDIO)")
        return bambu.slice_report(src, dst)
