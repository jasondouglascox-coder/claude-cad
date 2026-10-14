"""The office as built: walls, doors and the closed loop of track (four viaduct runs, the bridge corner and
three inside corners), placed in room coordinates for one review STEP.

Room frame (mm): x to the right, y toward the back, z up from the floor; the front wall's face is y = 0 and
is left out of the render. Measured in inches (see Room), converted here. The loop runs counterclockwise
from above: down the right wall toward the back, the bridge corner across the alcove mouth, along the back
wall to the left, then inside corners at the back-left, front-left and front-right with a run along each wall.
"""
import math
from dataclasses import dataclass

from build123d import Align, Axis, Box, Color, Compound, Location, Part, Plane, Polygon, Pos, Rot, extrude, revolve

from cadkit import paint
from hotrain import assembly
from hotrain import corner_assembly as CA
from hotrain import corner_layout as CL
from hotrain import layout as L
from hotrain.params import INCH, P, Params

def hex_color(h: str) -> Color:
    h = h.lstrip("#")
    return Color(*(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))


TEAL = hex_color("#adf7f5")  # the user's wall color
WHITE = hex_color("#f5f5f0")
IRON = hex_color("#c8c9cc")  # bridge structure: light gray, readable against the walls
TIE_BROWN = hex_color("#6e4f38")
NICKEL = hex_color("#5a5b60")  # rails: darker than the structure so they read
ALUMINUM = hex_color("#e2e4e8")


@dataclass(frozen=True)
class Room:
    """All in inches, as measured. The model is square: the front and left walls are derived from the others,
    and their own measurements only feed misfit()."""
    right_len: float = 170.0  # right wall (the long one, French doors), front to back
    alcove_w: float = 43.75  # back wall of the alcove (= alcove width, right wall to the short wall)
    alcove_depth: float = 43.75  # short wall, from the alcove's back wall toward the front
    back_len: float = 82.5  # back wall, running left from the bump-out corner
    front_len: float = 125.875  # measured; the model uses back_len + alcove_w
    left_len: float = 126.375  # measured; the model uses right_len - alcove_depth
    door_h: float = 84.0  # 7 ft doors
    above_door: float = 24.0
    rail_below_ceiling: float = 12.0
    french_from_back: tuple = (2.0, 65.0)  # double French door on the right wall, measured from the back wall
    door_from_short: float = 5.0  # door on the back wall, from its right (short-wall) end
    door_w: float = 35.0
    wall_t: float = 4.0

    @property
    def ceiling(self) -> float:
        return self.door_h + self.above_door

    def misfit(self) -> dict:
        """Model minus measured length (inches) of the two derived walls. Nonzero means the room isn't square
        (the front wall is 3/8" short, confirmed by three readings) or a reading is off."""
        return {"front": self.back_len + self.alcove_w - self.front_len,
                "left": self.right_len - self.alcove_depth - self.left_len}


MISFIT_TOL = 0.125  # inches: a tape reading's tolerance


def misfit_notes(r: Room = Room()) -> list[str]:
    return [f"note: the room isn't square; the real {wall} wall is {abs(d):.3f}\" {'shorter' if d > 0 else 'longer'} "
            f"than the square model (docs/measurements.md)" for wall, d in r.misfit().items() if abs(d) > MISFIT_TOL]


@dataclass(frozen=True)
class Section:
    name: str
    kind: str  # "run" | "inside" | "bridge"
    loc: Location  # section frame -> room
    bays: tuple = ()  # runs only
    ends: tuple = ()  # runs only


def _mm(v: float) -> float:
    return v * INCH


def _equal_bays(p: Params, total: float) -> tuple:
    n = max(1, math.ceil(total / p.max_bay_len))
    return tuple([total / n] * n)


def corner(s: Section) -> CL.Corner:
    return CL.bridge_corner() if s.kind == "bridge" else CL.inside_corner()


def _inside_loc(p: Params, x: float, y: float, z: float, heading: float) -> Location:
    """Inside corner placed by the room (x, y) where its two walls meet and the heading it is entered on."""
    reach = CL.curve_start_x(p, CL.inside_corner()) + p.curve_r + p.track_offset  # walls' corner, from P0
    return Pos(x, y, z) * Rot(0, 0, heading) * Pos(-reach, p.track_offset, 0)


def sections(p: Params = P, r: Room = Room()) -> list[Section]:
    """The loop in running order: each corner, then the run to the next corner. Every corner turns left."""
    o = p.track_offset
    xr = _mm(r.alcove_w + r.back_len)  # right wall face
    yb = _mm(r.right_len - r.alcove_depth)  # back wall face
    z_t = _mm(r.ceiling - r.rail_below_ceiling) - p.rail_top  # tie underside
    y_p0 = (yb - o) - (CL.curve_start_x(p, CL.bridge_corner()) + p.curve_r)
    corners = [  # (corner, run after it, heading in, corner frame -> room)
        (Section("bridge_corner", "bridge", Pos(xr - o, y_p0, z_t) * Rot(0, 0, 90)), "back_viaduct", 90),
        (Section("back_left_corner", "inside", _inside_loc(p, 0, yb, z_t, 180)), "left_viaduct", 180),
        (Section("front_left_corner", "inside", _inside_loc(p, 0, 0, z_t, -90)), "front_viaduct", -90),
        (Section("front_right_corner", "inside", _inside_loc(p, xr, 0, z_t, 0)), "right_viaduct", 0),
    ]
    out = []
    for (c, run, heading), (nxt, _, _) in zip(corners, corners[1:] + corners[:1]):
        pn = CL.portals(p, corner(c))[-1]
        a, b = (c.loc * Pos(pn.x, pn.y, 0)).position, nxt.loc.position  # next corner's P0 is its origin
        ln = math.dist((a.X, a.Y), (b.X, b.Y))
        out.append(c)
        out.append(Section(run, "run", Pos(a.X, a.Y, z_t) * Rot(0, 0, heading + 90), _equal_bays(p, ln),
                           (L.CORNER, L.CORNER)))
    return out


def track_ends(p: Params, s: Section) -> tuple:
    """Room (x, y) of the track centerline where the section starts and ends."""
    if s.kind == "run":
        a, b = 0.0, sum(s.bays)
        pa, pb = s.loc * Pos(a, 0, 0), s.loc * Pos(b, 0, 0)
    else:
        ps = CL.portals(p, corner(s))
        pa, pb = s.loc * Pos(ps[0].x, ps[0].y, 0), s.loc * Pos(ps[-1].x, ps[-1].y, 0)
    return (pa.position.X, pa.position.Y), (pb.position.X, pb.position.Y)


def _rail_face(p: Params) -> Polygon:
    """Code 100 rail cross-section (u across, z up from the tie underside), centered on u = 0."""
    z0 = p.tie_h + p.tie_plate_h
    hb, wb, hh = p.rail_base_w / 2, 0.25, p.rail_head_w / 2
    zb, zh = z0 + 0.5, z0 + p.rail_height - 0.75
    pts = [(-hb, z0), (hb, z0), (hb, zb), (wb, zb), (wb, zh), (hh, zh), (hh, z0 + p.rail_height),
           (-hh, z0 + p.rail_height), (-hh, zh), (-wb, zh), (-wb, zb), (-hb, zb)]
    return Polygon(*pts, align=None)


def _straight_rail(p: Params, u: float, x0: float, x1: float) -> Part:
    return Pos(x0, 0, 0) * extrude(Plane.YZ * (Pos(u, 0) * _rail_face(p)), x1 - x0)


def rails(p: Params, s: Section) -> list[Part]:
    """Both rails of a section, in room coordinates."""
    out = []
    for u in p.rail_ys:
        if s.kind == "run":
            lo, hi = L.run_extent(p, list(s.bays), s.ends)
            out.append(s.loc * _straight_rail(p, u, lo, hi))
            continue
        c = corner(s)
        x1, r = CL.curve_start_x(p, c), p.curve_r
        parts = [_straight_rail(p, u, 0.0, x1)]
        arc = revolve(Plane.XZ * (Pos(r - u, 0) * _rail_face(p)), Axis.Z, 90)
        parts.append(Pos(x1, r, 0) * Rot(0, 0, -90) * arc)
        exit_len = c.n_out * p.bow_span
        parts.append(Pos(x1 + r - u, r, 0) * Rot(0, 0, 90) * _straight_rail(p, 0.0, 0.0, exit_len))
        for q in parts:
            out.append(s.loc * q)
    return out


def _box(x0, x1, y0, y1, z0, z1) -> Part:
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.MIN, Align.MIN, Align.MIN))


def walls(r: Room = Room()) -> list[tuple[str, Part, Color]]:
    t = r.wall_t
    xr, yback = r.alcove_w + r.back_len, r.right_len
    yb, xs = yback - r.alcove_depth, r.back_len  # back wall face; short wall face
    h = r.ceiling
    f0, f1 = yback - r.french_from_back[1], yback - r.french_from_back[0]
    d1 = xs - r.door_from_short
    d0 = d1 - r.door_w
    mm = lambda *v: [_mm(a) for a in v]
    right = _box(*mm(xr, xr + t, 0, yback + t, 0, h)) - _box(*mm(xr - 1, xr + t + 1, f0, f1, 0, r.door_h))
    back = _box(*mm(-t, xs, yb, yb + t, 0, h)) - _box(*mm(d0, d1, yb - 1, yb + t + 1, 0, r.door_h))
    out = [
        ("wall_right", right, TEAL),
        ("wall_alcove_back", _box(*mm(xs - t, xr + t, yback, yback + t, 0, h)), TEAL),
        ("wall_alcove_short", _box(*mm(xs - t, xs, yb, yback, 0, h)), TEAL),
        ("wall_back", back, TEAL),
        ("wall_left", _box(*mm(-t, 0, 0, yb + t, 0, h)), TEAL),
    ]
    # doors, set back 1" into their openings; the French door is two leaves
    mid = (f0 + f1) / 2
    out += [
        ("french_door_left_leaf", _box(*mm(xr + 1, xr + 2.75, f0, mid - 0.125, 0, r.door_h)), WHITE),
        ("french_door_right_leaf", _box(*mm(xr + 1, xr + 2.75, mid + 0.125, f1, 0, r.door_h)), WHITE),
        ("door", _box(*mm(d0, d1, yb + 1, yb + 2.75, 0, r.door_h)), WHITE),
    ]
    return out


def front_wall(r: Room = Room()) -> Part:
    """For clash checks only: the front wall stays out of the render."""
    t, xr = r.wall_t, r.alcove_w + r.back_len
    return _box(*[_mm(v) for v in (-t, xr + t, -t, 0, 0, r.ceiling)])


def _color_for(name: str) -> Color:
    if name.startswith("deck") and name.endswith("_steel"):
        return IRON  # corner deck edge beams, rod runners and tie plates
    if "ladder" in name or name.startswith("deck"):
        return TIE_BROWN
    if name.startswith("rod_") or name.startswith("cable"):
        return ALUMINUM
    if name.startswith("line") or name.startswith("ceiling_anchor"):
        return WHITE  # white braid and anchors against the ceiling
    return IRON


def section_parts(p: Params, s: Section) -> list[tuple[str, Part]]:
    """Every part of a section placed in the room (no rails)."""
    if s.kind == "run":
        items = assembly.placed_parts(p, list(s.bays), s.ends)
    else:
        c = corner(s)
        items = CA.placed_parts(p, c) + CA.cables(p, c)
    return [(n, s.loc * part) for n, part in items]


def make(p: Params = P, r: Room = Room(), display: bool = False) -> Compound:
    """Whole office. display=True splits painted two-color parts into colored bodies (for viewers that
    color whole shapes only); the default keeps them as single painted parts (STEP/Onshape)."""
    groups = []
    for s in sections(p, r):
        kids = []
        for n, part in section_parts(p, s):
            part.color = _color_for(n)
            split = paint.display_parts(part) if display else None
            if split:
                for body, col in split:
                    body.color, body.label = col, n
                    kids.append(body)
                continue
            kids.append(part)
        for rail in rails(p, s):
            rail.color, rail.label = NICKEL, "code_100_rail"
            kids.append(rail)
        groups.append(Compound(children=kids, label=s.name))
    wall_kids = []
    for n, part, col in walls(r):
        part.color, part.label = col, n
        wall_kids.append(part)
    groups.append(Compound(children=wall_kids, label="room"))
    return Compound(children=groups, label="office")


def section_models(p: Params = P, r: Room = Room()) -> list[tuple[str, Compound]]:
    """One colored Compound per track section plus one for the room (walls and doors)."""
    out = []
    for s in sections(p, r):
        kids = []
        for n, part in section_parts(p, s):
            part.color = _color_for(n)
            kids.append(part)
        for rail in rails(p, s):
            rail.color, rail.label = NICKEL, "code_100_rail"
            kids.append(rail)
        out.append((s.name, Compound(children=kids, label=s.name)))
    wall_kids = []
    for n, part, col in walls(r):
        part.color, part.label = col, n
        wall_kids.append(part)
    out.append(("room", Compound(children=wall_kids, label="room")))
    return out


def _split(comp: Compound, parts: int) -> list[Compound]:
    """Split a section into roughly equal pieces along its longest axis (keeps web files small)."""
    kids = list(comp.children)
    bb = comp.bounding_box()
    axis = max(range(3), key=lambda i: (bb.size.X, bb.size.Y, bb.size.Z)[i])
    key = lambda k: (k.bounding_box().center().X, k.bounding_box().center().Y, k.bounding_box().center().Z)[axis]
    kids.sort(key=key)
    n = len(kids)
    return [Compound(children=kids[i * n // parts:(i + 1) * n // parts], label=f"{comp.label}_{i}") for i in range(parts)]


def export_glbs(p: Params, folder, max_mb: float = 8.0) -> list:
    """Write each section as binary glTF (meshes with colors). Sections bigger than max_mb are split."""
    from pathlib import Path
    from build123d import export_gltf
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, comp in section_models(p):
        path = folder / f"{name}.glb"
        export_gltf(comp, str(path), binary=True, linear_deflection=0.5, angular_deflection=0.5)
        mb = path.stat().st_size / 1e6
        if mb <= max_mb:
            paths.append(path)
            continue
        path.unlink()
        pieces = int(mb // max_mb) + 1
        for i, piece in enumerate(_split(comp, pieces)):
            pp = folder / f"{name}_{i}.glb"
            export_gltf(piece, str(pp), binary=True, linear_deflection=0.5, angular_deflection=0.5)
            paths.append(pp)
    return paths


def glb_to_json(glb_path, json_path) -> None:
    """Rewrite a .glb as self-contained glTF JSON (buffer embedded as a data URI), for hosts that only
    serve .json. Three.js's GLTFLoader reads it unchanged."""
    import base64
    import json
    import struct
    from pathlib import Path
    b = Path(glb_path).read_bytes()
    ln = struct.unpack("<I", b[12:16])[0]
    doc = json.loads(b[20:20 + ln])
    off = 20 + ln
    bin_len = struct.unpack("<I", b[off:off + 4])[0]
    data = b[off + 8:off + 8 + bin_len]
    doc["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(data).decode()
    Path(json_path).write_text(json.dumps(doc, separators=(",", ":")))


LABELS = {"room": "Walls & doors", "bridge_corner": "Bridge corner", "back_left_corner": "Back-left corner",
          "front_left_corner": "Front-left corner", "front_right_corner": "Front-right corner",
          "back_viaduct": "Back wall run", "right_viaduct": "Right wall run", "left_viaduct": "Left wall run",
          "front_viaduct": "Front wall run"}
LOAD_ORDER = ["room", "bridge_corner", "back_left_corner", "front_left_corner", "front_right_corner",
              "back_viaduct", "right_viaduct", "left_viaduct", "front_viaduct"]


def build_web(p: Params, out) -> "Path":
    """out/web: the phone/web 3D viewer page plus its models as self-contained glTF JSON and a manifest.
    Publish out/web/office-viewer.html with every models/*.json attached (artifacts don't serve .glb)."""
    import json
    import shutil
    from pathlib import Path
    out = Path(out)
    web, models = out / "web", out / "web" / "models"
    if models.exists():
        shutil.rmtree(models)
    models.mkdir(parents=True)
    names = []
    for glb in export_glbs(p, out / "glb"):
        glb_to_json(glb, models / f"{glb.stem}.json")
        names.append(f"{glb.stem}.json")
    manifest = []
    for sec in LOAD_ORDER:
        fs = sorted(n for n in names if n == f"{sec}.json" or n.startswith(sec + "_"))
        manifest.append({"id": sec, "label": LABELS[sec],
                         "files": [{"path": f"models/{f}", "mb": round((models / f).stat().st_size / 1e6, 2)} for f in fs]})
    (models / "manifest.json").write_text(json.dumps(manifest, indent=1))
    page = Path(__file__).resolve().parent.parent / "web" / "office-viewer.html"
    shutil.copy(page, web / "office-viewer.html")
    return web
