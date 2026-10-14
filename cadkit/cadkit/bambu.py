"""Check a 3MF the way the slicer reads it: drive Bambu Studio's command line.

Unit tests can't tell you what Bambu Studio will do with a file. These can:

- `roundtrip(src)`: Bambu loads the file and saves it back. Compare with `bambu3mf.read_filaments` and
  `bambu3mf.object_sizes`: a filament or a mesh it didn't understand comes back different.
- `slice_report(src)`: Bambu slices plate 1 and reports grams per filament and which filaments print on which
  layers, e.g. a two-color ladder: brown layers 0-11, gray 12-18, one change.

Set BAMBU_STUDIO to the executable if it isn't in the default place. The CLI writes result.json into its working
directory, so it runs in a temp dir.
"""
import os
import platform
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

DEFAULT = {"Darwin": "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"}


def find() -> Path | None:
    p = os.environ.get("BAMBU_STUDIO") or DEFAULT.get(platform.system())
    return Path(p) if p and Path(p).exists() else None


def _run(args: list[str], timeout: int = 600) -> None:
    exe = find()
    if exe is None:
        raise FileNotFoundError("Bambu Studio not found; set BAMBU_STUDIO to its executable")
    with tempfile.TemporaryDirectory() as cwd:
        r = subprocess.run([str(exe), *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f"Bambu Studio exited {r.returncode}: {' '.join(args)}\n{r.stdout[-2000:]}")


def roundtrip(src: Path, dst: Path | None = None) -> Path:
    """Load src in Bambu Studio and save it back as dst (default: next to src, '.roundtrip.3mf')."""
    src = Path(src).resolve()
    dst = Path(dst or src.with_suffix(".roundtrip.3mf")).resolve()
    _run(["--export-3mf", str(dst), str(src)])
    return dst


def slice_report(src: Path, dst: Path | None = None) -> dict:
    """Slice plate 1. Returns {"grams": {filament: g}, "layers": [(filaments, first layer, last layer)]},
    filaments numbered from 1 as in the slicer's list."""
    src = Path(src).resolve()
    dst = Path(dst or src.with_suffix(".sliced.3mf")).resolve()
    _run(["--slice", "1", "--export-3mf", str(dst), str(src)])
    info = ET.fromstring(zipfile.ZipFile(dst).read("Metadata/slice_info.config"))
    grams = {int(f.get("id")): float(f.get("used_g")) for f in info.iter("filament")}
    layers = []
    for el in info.iter("layer_filament_list"):
        lo, hi = (int(v) for v in el.get("layer_ranges").split())
        layers.append((tuple(int(i) + 1 for i in el.get("filament_list").split()), lo, hi))  # file is 0-based
    return {"grams": grams, "layers": sorted(layers, key=lambda r: r[1])}
