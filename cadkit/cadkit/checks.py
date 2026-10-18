"""Printability checks shared by part tests. Each returns what's wrong, so a test can assert it's empty/zero."""
from collections import Counter

import numpy as np
from build123d import Align, Box, Pos, Shape, Vector

from cadkit.printer import Printer, default


def printable_problems(part: Shape, printer: Printer | None = None) -> list[str]:
    """Why this part can't go straight to the printer as exported (print orientation). Empty list = fine.
    printer: default = the one in your settings."""
    printer = printer or default()
    probs = []
    if not part.is_valid:
        probs.append("invalid solid")
    if len(part.solids()) != 1:
        probs.append(f"{len(part.solids())} separate solids (expected 1)")
    bb = part.bounding_box()
    if abs(bb.min.Z) > 1e-6:
        probs.append(f"not on the bed: min Z = {bb.min.Z:.3f}")
    if bb.min.X < -1e-6 or bb.min.Y < -1e-6:
        probs.append("extends into negative X/Y")
    if bb.max.X > printer.usable_x or bb.max.Y > printer.usable_y:
        probs.append(f"footprint {bb.max.X:.1f} x {bb.max.Y:.1f} mm exceeds the usable bed "
                     f"{printer.usable_x:.0f} x {printer.usable_y:.0f} mm")
    return probs


def open_edges(shape: Shape, tol: float = 1e-4) -> int:
    """Mesh edges not shared by exactly two triangles (0 = watertight). Catches edge-to-edge unions, which make
    valid B-reps but meshes the slicer rejects."""
    bad = 0
    for s in shape.solids():
        verts, tris = s.tessellate(0.05, 0.2)
        v = np.round(np.array([(q.X, q.Y, q.Z) for q in verts]) / tol).astype(np.int64)
        _, idx = np.unique(v, axis=0, return_inverse=True)
        idx = idx.ravel()
        edges = Counter()
        for t in tris:
            a, b, c = (int(idx[i]) for i in t)
            for e in ((a, b), (b, c), (c, a)):
                edges[tuple(sorted(e))] += 1
        bad += sum(1 for n in edges.values() if n != 2)
    return bad


def off_layer_z(shape: Shape, printer: Printer | None = None) -> list[float]:
    """Z of every horizontal face that isn't on a layer boundary (a slicer splits that layer)."""
    printer = printer or default()
    out = set()
    for f in shape.faces():
        n = f.normal_at()
        if abs(abs(n.Z) - 1) < 1e-9:
            z = f.center().Z
            if not printer.on_layer(z):
                out.add(round(z, 4))
    return sorted(out)


def unsupported(upper: Shape, lower: Shape, probe: float = 0.1) -> float:
    """Volume (mm^3) of the upper color's bottom layer that has no lower color under it. Two-color parts print the
    lower color first; anything the upper color starts over air needs supports. 0 = fine."""
    bb = upper.bounding_box()
    mn = (Align.MIN, Align.MIN, Align.MIN)
    slab = upper & (Pos(bb.min.X - 1, bb.min.Y - 1, bb.min.Z) * Box(bb.size.X + 2, bb.size.Y + 2, probe, align=mn))
    below = Pos(0, 0, -2 * probe) * slab
    return below.volume - (below & lower).volume


def downward_faces(part: Shape) -> list[tuple[float, float]]:
    """(z, area) of every face facing straight down above the bed: each one is a bridge or needs support. For
    review: list them, then check each spans less than a few mm between supports."""
    out = []
    for f in part.faces():
        n = f.normal_at()
        if n.Z < -1 + 1e-9 and f.center().Z > 1e-6:
            out.append((round(f.center().Z, 4), round(f.area, 3)))
    return sorted(out)


def overhangs(part: Shape, max_deg: float = 45.0) -> list[tuple[float, float]]:
    """(z, area) of every face with an underside steeper than max_deg from vertical, above the bed: angled
    overhangs that need support. Flat ones (bridges) are downward_faces; a 45° roof or flare prints fine."""
    limit = np.sin(np.radians(max_deg)) + 1e-3
    out = []
    for f in part.faces():
        verts, tris = f.tessellate(0.05, 0.2)
        v = np.array([(q.X, q.Y, q.Z) for q in verts])
        area = 0.0
        for t in tris:
            a, b, c = v[list(t)]
            n = np.cross(b - a, c - a)
            size = np.linalg.norm(n)
            if size < 1e-12 or max(a[2], b[2], c[2]) <= 1e-6:  # on the bed
                continue
            if -n[2] / size > limit and -f.normal_at(Vector(*((a + b + c) / 3))).Z > limit:  # facets tilt; confirm
                area += size / 2
        if area > 0:
            out.append((round(f.center().Z, 4), round(area, 3)))
    return sorted(out)


ADVICE = ("Options: split the colors by height (one color up to a Z, the next above it, one swap per seam); print "
          "the detail as a separate part and glue it on; drop a color; or accept the cost for this plate "
          "(color_changes= in write_plates, or CADKIT_COLOR_CHANGES).")


def color_problems(items: list, colors: int | None = None, changes: int | None = None,
                   printer: Printer | None = None) -> list[str]:
    """What a plate's [(name, shape)] asks of the printer beyond your setup: more colors than it has, or more swaps
    than the budget (settings: colors, color_changes). Each message says what to do instead. Empty list = fine."""
    from cadkit.plates import color_changes, colors_used
    from cadkit.settings import settings
    colors = settings().colors if colors is None else colors
    changes = settings().color_changes if changes is None else changes
    probs = []
    n = colors_used(items)
    if n > colors:
        probs.append(f"{n} colors, but the printer has {colors} (CADKIT_COLORS). With 1, everything prints on "
                     f"filament 1 in its shape. " + ADVICE)
    k = color_changes(items, printer)
    if colors > 1 and k > changes:
        probs.append(f"{k} color changes, over the budget of {changes} (CADKIT_COLOR_CHANGES): each costs time and "
                     f"purged filament. " + ADVICE)
    return probs
