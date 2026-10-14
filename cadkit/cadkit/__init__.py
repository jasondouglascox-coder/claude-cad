"""cadkit: the reusable half of claude-cad.

Print-ready output and checks for build123d parts, learned the hard way on a room-sized model railroad:

- `printer`: the machine (bed, margin, layer height); Bambu Lab A1 by default.
- `shapes`: 2D profile helpers (`rect`, `poly`, `bowtie`, `dovetail`) for flat-printed parts.
- `checks`: printable on the bed, watertight mesh, layer-height Z levels, upper color resting on the lower one.
- `clash`: pairwise interference for assembly tests.
- `paint`: two-color parts as one painted solid (STEP face colors) or split bodies (viewers, printer files).
- `plates`: MaxRects bed packing that keeps two-color parts off single-color plates.
- `bambu3mf`: plates as Bambu Studio projects with a filament per part, so they open already colored.
- `bambu`: drive Bambu Studio's command line to check a 3MF the way the slicer reads it.
- `export`: STEP / SVG preview / plate writers. `view`: send shapes to OCP CAD Viewer.
"""
from cadkit.printer import A1, Printer

__all__ = ["A1", "Printer"]
