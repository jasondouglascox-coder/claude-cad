# build123d patterns and traps (build123d 0.13.0, Python 3.12)

Everything here was verified while building `demo/near-ceiling-track`. When in doubt, spike it in a scratch script first. A 10-line probe is cheaper than a wrong plan.

## Setup

```bash
uv init --python 3.12 && uv python pin 3.12 && uv add build123d==0.13.0 && uv add --dev pytest
# pyproject: [tool.pytest.ini_options] pythonpath = ["."]  testpaths = ["tests"]
```

## 2D profile → part (algebra mode)

```python
from build123d import Align, Bezier, Face, Line, Wire, Polygon, Pos, Rot, Rectangle, Sketch, extrude

def rect(u0, u1, v0, v1):  # corner-to-corner rectangle
    return Pos(u0, v0) * Rectangle(u1 - u0, v1 - v0, align=(Align.MIN, Align.MIN))

def poly(*pts):  # ALWAYS use this for non-rectangles: forces counter-clockwise
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return Polygon(*(pts if area > 0 else pts[::-1]), align=None)

prof = (Sketch() + [rect(...), rect(...)]) - [cut1, cut2]   # many shapes: Sketch() + list is fast
part = extrude(prof, thickness)                              # print orientation: flat on Z=0
```

**Trap: a clockwise Polygon extrudes toward −Z.** The part splits into separate solids and nothing errors. Symptom: `len(part.solids()) > 1` or `bbox.min.Z < 0`. Hence `poly()`.

**Trap: edge-to-edge unions** (a brace that meets a flange exactly at a corner or edge) give a valid B-rep but an **invalid 3MF mesh** ("3mf mesh is invalid"). Overlap members by ~1 mm and give joints real width (a brace touching its flange at a single point got through every test once).

Curved band (e.g. an arch rib): Bezier lower edge, the same curve shifted up by the thickness for the upper edge, closed with Lines, then `Face(Wire([...]))`. For a constant-thickness band, shift **every** control point by the thickness (shifting only the middle one by 2× made the crown 1.5 mm too thick).

Offsetting a profile for clearance: `offset(sketch, c, kind=Kind.INTERSECTION)` keeps sharp corners.

## Swept / curved 3D

- Straight extrusion along X of a YZ profile: `extrude(Plane.YZ * profile, length)` (Plane.YZ: x_dir = +Y, normal = +X).
- Arc sweep: put the profile on `Plane.XZ` at x = radius, `revolve(face, Axis.Z, sweep_deg)`, then `Pos(center) * Rot(0, 0, start_deg) * part`. This was used for rod channels and curved rails, and matches the true arc exactly.
- Holes through a flat part's edge (screw slots in a flange): `extrude(Plane.YZ * Pos(...) * SlotCenterToCenter(len, d), thickness)`.

## Locations

- `Location * shape` returns a moved copy, so read composition right to left: `Pos(x, y, z) * Rot(0, 0, 90) * Rot(90, 0, 0) * Pos(...)`.
- Print frame → assembly frame recipes that worked:
  - A panel printed flat (profile in XY, thickness in Z) standing vertical along X: `Pos(x0, y_c, z_off) * Pos(0, t/2, 0) * Rot(90, 0, 0)`. Mirror it to the other end with an extra `Rot(0, 0, 180)`.
  - A transverse plate (profile x→Y, y→Z, thickness → X): `Pos(x, 0, 0) * Rot(0, 0, 90) * Rot(90, 0, 0) * Pos(-ymin, -h, -t/2)`.
- Always test placement with bounding boxes (min/max per axis), and test mating with `distance_to` (≈ 0 means touching) plus intersection volume (≈ 0 means no overlap).
- `Vector` is not subscriptable: use `.X/.Y/.Z`. `pytest.approx(0)` needs `abs=`.

## Checks

```python
def printable_problems(part, p):
    probs = []
    if not part.is_valid: probs.append("invalid solid")
    if len(part.solids()) != 1: probs.append("multiple solids")
    bb = part.bounding_box()
    if abs(bb.min.Z) > 1e-6: probs.append("not on bed")
    if bb.min.X < -1e-6 or bb.min.Y < -1e-6: probs.append("negative X/Y")
    if bb.max.X > p.bed - p.bed_margin or bb.max.Y > p.bed - p.bed_margin: probs.append("too big")
    return probs
```

- Measure features with probes: `(part & Pos(...) * Box(0.2, L, 0.2, align=MIN)).solids()`, then compare the pieces' bounding boxes (gauge between shoulders, slot widths).
- Clash finder: bbox-overlap prefilter, then `(a & b).volume > 1e-3`. Exclude pairs that overlap by construction (e.g. consecutive wire segments).
- Envelopes: a moving car is a `Box` at each step along the path; wires are boxes between hook points; cables are `Cylinder(..., align=(CENTER, CENTER, MIN))`. Don't combine `align=None` with `.moved()`, which shifted a cable twice and made its test vacuous.

## Export

```python
from build123d import Color, Compound, ExportSVG, LineType, Mesher, export_step, export_stl
part.label = "bracket"                 # becomes the STEP PRODUCT name (Onshape part name)
part.color = Color(0.16, 0.52, 0.52)   # written as COLOUR_RGB
export_step(Compound(children=[...], label="run"), "out/step/run.step")   # nested Compounds = assembly tree
m = Mesher(); m.add_shape(part); m.write("x.3mf")                          # for Bambu Studio
visible, hidden = shape.project_to_viewport(origin, viewport_up=up, look_at=center)
exp = ExportSVG(scale=800/span); exp.add_layer("v"); exp.add_layer("h", line_color=(0.63,)*3, line_type=LineType.ISO_DOT)
exp.add_shape(visible, layer="v"); exp.add_shape(hidden, layer="h"); exp.write("p.svg")   # then: rsvg-convert -b white -w 1400 p.svg -o p.png
```

- **Trap: placed copies share one underlying shape, and STEP names it once (the last label wins).** Label base shapes by part type, not by instance.
- Hidden-line SVGs of a whole room are slow; render subsets.
- Big colored assemblies (~200 MB STEP): upload the plain .step; Onshape rejected a zipped one. Colors come through from COLOUR_RGB; to recolor afterwards in Onshape, select parts → right-click → Edit appearance, or change the colors in code and re-import.

## Plate packing

MaxRects best-short-side-fit: items inflated by a 3 mm gap, both rotations tried, free rectangles split and pruned. Nest awkward pairs first (two arch halves head-to-tail, found by binary-searching the lift with `distance_to >= gap`). Dedupe kits with a geometry key (relative tie/tab positions, lengths) and print quantities. Write each plate as STEP + 3MF.

## Web (glTF) export

```python
from build123d import export_gltf
export_gltf(compound, "x.glb", binary=True, linear_deflection=0.5, angular_deflection=0.5)  # mm model -> meters, Y-up, colors kept
```
Coarse deflection (0.5 mm / 0.5 rad) keeps a whole viaduct section around 6–13 MB; the tiny tie-plate boxes dominate size. To host on a claude.ai Artifact, convert to self-contained glTF JSON: read the GLB's JSON chunk and BIN chunk, then set `buffers[0].uri = "data:application/octet-stream;base64,..."`. GLTFLoader loads it from a `.json` URL.

## Watertight-mesh check (catches the edge-to-edge trap before the slicer does)

```python
import numpy as np
from collections import Counter
def non_manifold_edges(shape, tol=1e-4):
    bad = 0
    for s in shape.solids():
        verts, tris = s.tessellate(0.05, 0.2)
        V = np.round(np.array([(v.X, v.Y, v.Z) for v in verts]) / tol).astype(np.int64)
        _, idx = np.unique(V, axis=0, return_inverse=True); idx = idx.ravel()
        edges = Counter(tuple(sorted((int(idx[a]), int(idx[b])))) for t in tris for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])))
        bad += sum(1 for n in edges.values() if n != 2)
    return bad
```

## Two-color (AMS) parts

- Model the part as two bodies split by height (`wood` up to Z, `steel` above), so the print has one color change.
- **3MF:** write both bodies as ONE object with two parts. `Mesher.add_shape` makes one build item per shape, so
  remove those items (`model.GetBuildItems()` / `RemoveBuildItem`), add a `ComponentsObject` holding both meshes,
  and add one build item for it. Otherwise the slicer drops the upper body onto the bed.
- **STEP:** fuse the bodies into one solid (`a + b`; build123d 0.13 doesn't merge coplanar faces, so each face stays
  on one side of the seam). Color each face by testing a point on it (the centroid of its first tessellation triangle)
  with `solid.is_inside(pt, tol)`; ON counts as inside. build123d only colors whole shapes, so add face colors to
  the XCAF document from `_create_xde()`: walk the shape labels with `TDF_ChildIterator(shape_tool.BaseLabel())`,
  then `AddSubShape(label, face)` and `SetColor(sub, color, XCAFDoc_ColorSurf)`. Key the colors by `hash(face)`
  of the unplaced prototype; placed copies share its faces. `TDF_LabelSequence` isn't exposed by this OCP build.
- **Viewers** that only color whole shapes need the split bodies, placed with the copy's location
  (`Location(placed.wrapped.Location())`, matched with `placed.wrapped.IsPartner(proto.wrapped)`).

## Misc traps

- `extrude` of a Compound returns a Compound; wrap results with `Part(x.solids())` before boolean chains, or you
  get "Dimensions of objects ... are inconsistent".
- A `Text` along a path: `Text(s, font_size, font_path=..., path=arc_edge, position_on_path=0.5)`.
- `Color` has no `.to_tuple()`; use `tuple(color)` (RGBA).
- Write CSVs with `encoding="utf-8"`. Test workers (pytest-xdist) may run with an ASCII locale and fail on "±".
