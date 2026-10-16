"""cadkit: the reusable half of claude-cad.

Print-ready output and checks for build123d parts, learned the hard way on a room-sized model railroad:

- `settings`: your setup (printer, colors, slicer, projects folder) from CADKIT_* variables or cadkit.toml.
- `printer`: the machine (bed, margin, layer height); defaults from settings, a Bambu Lab A1 if unset.
- `shapes`: 2D profile helpers (`rect`, `poly`, `bowtie`, `dovetail`) for flat-printed parts.
- `checks`: printable on the bed, watertight mesh, layer-height Z levels, upper color resting on the lower one.
- `clash`: pairwise interference for assembly tests.
- `paint`: two-color parts as one painted solid (STEP face colors) or split bodies (viewers, printer files).
- `plates`: MaxRects bed packing that keeps multi-color parts off single-color plates; color swap counts.
- `bambu3mf`: plates as Bambu Studio projects with a filament per part, so they open already colored.
- `bambu`: drive Bambu Studio's command line to check a 3MF the way the slicer reads it.
- `slicers`: one interface for any slicer (`active()`); Bambu Studio built in, others by PR.
- `render`: shaded PNG previews. `new`: start a project from the template.
- `export`: STEP / SVG preview / plate writers. `view`: send shapes to OCP CAD Viewer.
"""
from cadkit.printer import A1, Printer

__all__ = ["A1", "Printer"]
