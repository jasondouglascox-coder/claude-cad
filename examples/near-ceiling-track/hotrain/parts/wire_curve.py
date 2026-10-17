"""Curve test piece for the stainless wire rail: an 18° arc of the corner radius, printed flat. Brown ties and runners
(like the decks), the gray wire web along each rail's true arc, and a jigsaw tab on each runner so identical pieces
chain into the 90° corner. The wire is laid in after printing and runs over the joints.
docs/specs/2026-10-16-wire-rail-design.md

Curve frame: the curve centre at the origin, the piece symmetric about +Y, z = 0 at the tie underside. The track
runs clockwise, from the start (left, socket) to the end (right, tab)."""
import math
from functools import lru_cache

from build123d import Axis, Circle, Compound, Part, Plane, Pos, Rectangle, Rot, Sketch, extrude, revolve

from hotrain import wire_rail as W
from hotrain.joints import jigsaw, poly, rect
from hotrain.params import P, Params


def _ends(p: Params) -> tuple[float, float]:
    """(start, end) polar angles in degrees."""
    return 90 + p.wire_test_deg / 2, 90 - p.wire_test_deg / 2


def _sweep(p: Params, section) -> Part:
    """Revolve a (radius, z) section over the piece's arc."""
    s, e = _ends(p)
    return Rot(0, 0, e) * revolve(Plane.XZ * section, Axis.Z, p.wire_test_deg)


def _at(p: Params, r: float, deg: float) -> tuple[float, float]:
    return r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg))


def tie_angles(p: Params) -> list[float]:
    s, _ = _ends(p)
    n = max(1, round(p.curve_r * math.radians(p.wire_test_deg) / p.tie_pitch))
    return [s - (k + 0.5) * p.wire_test_deg / n for k in range(n)]


def rail_radii(p: Params) -> tuple[float, float]:
    """(inner, outer) wire centre radii."""
    return p.curve_r - W.y_wire(p), p.curve_r + W.y_wire(p)


def _jig(p: Params, deg: float, r: float, clearance: float = 0.0) -> Sketch:
    """Jigsaw on the runner at radius r, its neck on the radial line at deg, pointing along the track."""
    x, y = _at(p, r, deg)
    return Pos(x, y) * Rot(0, 0, deg - 90) * jigsaw(p, 0.0, 0.0, clearance)


def _sockets(p: Params) -> list[Sketch]:
    s, _ = _ends(p)
    return [_jig(p, s, r, p.fit_snap) for r in rail_radii(p)]


def _web_section(p: Params, r: float, field: int):
    """The gray web's cross-section for the rail at radius r; field = +1 outward, -1 toward the centre."""
    return poly(*[(r + field * x, p.rail_top + z) for x, z in W.profile_pts(p)])


@lru_cache(maxsize=None)
def bodies(p: Params = P) -> dict[str, Part]:
    """The piece in the curve frame as two print colors: "wood" (ties, runners, tabs: up to the tie tops) and "steel"
    (the wire webs, all above): one color change."""
    _, e = _ends(p)
    ties = [Pos(*_at(p, p.curve_r, a)) * Rot(0, 0, a) * Rectangle(p.tie_l, p.tie_w) for a in tie_angles(p)]
    tabs = [_jig(p, e, r) for r in rail_radii(p)]
    wood = extrude(Sketch() + ties + tabs, p.tie_h)
    for r in rail_radii(p):
        wood += _sweep(p, Pos(r, p.tie_h / 2) * Rectangle(p.runner_w, p.tie_h))
    sockets = extrude(Sketch() + _sockets(p), p.rail_top + 1)
    wood = Part((wood - sockets).solids())
    inner, outer = rail_radii(p)
    steel = _sweep(p, _web_section(p, outer, 1)) + _sweep(p, _web_section(p, inner, -1))
    s, _ = _ends(p)
    over = [Pos(*_at(p, r, s)) * Rot(0, 0, s - 90) * rect(-1.0, p.jig_len + p.fit_snap + 0.2, -p.jig_head, p.jig_head)
            for r in rail_radii(p)]  # the web stops short of each socket's full length and width: never over air
    steel = Part((steel - extrude(Sketch() + over, p.rail_top + 1)).solids())
    return {"wood": wood, "steel": steel}


def make_assembly_piece(p: Params = P) -> Part:
    """Both colors fused, in the curve frame."""
    b = bodies(p)
    return b["wood"] + b["steel"]


def _offset(p: Params) -> tuple[float, float, float]:
    bb = make_assembly_piece(p).bounding_box()
    return -bb.min.X, -bb.min.Y, -bb.min.Z


def make(p: Params = P) -> Part:
    """Print orientation: tie undersides on the bed, webs up."""
    return Pos(*_offset(p)) * make_assembly_piece(p)


def make_colored(p: Params = P) -> Compound:
    """Print orientation like make(), as brown wood + gray steel bodies for the AMS."""
    from hotrain.room import IRON, TIE_BROWN
    b, off, out = bodies(p), _offset(p), []
    for name, col in (("wood", TIE_BROWN), ("steel", IRON)):
        part = Pos(*off) * b[name]
        part.label, part.color = f"wire_curve_{name}", col
        out.append(part)
    return Compound(children=out, label="wire_curve")


def wires(p: Params = P) -> list[Part]:
    """The two wires as laid in, curve frame (not printed)."""
    r = p.wire_d / 2
    return [_sweep(p, Pos(rr, p.rail_top - r) * Circle(r)) for rr in rail_radii(p)]


def wheelset(p: Params, depth: float, shift: float) -> list[Part]:
    """Two wheels and the axle at mid-piece on the radial line (+Y), riding the wires, shifted `shift` outward."""
    zc = p.rail_top + W.ride_height(p, depth, shift)
    w = W.wheel_solid(p, depth)
    y = p.curve_r + shift
    outer = Pos(0, y + p.wheel_b / 2, zc) * Rot(-90, 0, 0) * w
    inner = Pos(0, y - p.wheel_b / 2, zc) * Rot(90, 0, 0) * w
    cone = p.axle_d / 2 / math.tan(math.radians(30))
    hl = p.axle_l / 2
    ax = poly((0, -hl), (0.15, -hl), (p.axle_d / 2, -hl + cone), (p.axle_d / 2, hl - cone), (0.15, hl), (0, hl))
    axle = Pos(0, y, zc) * Rot(-90, 0, 0) * revolve(Plane.XZ * ax, Axis.Z, 360)
    return [outer, inner, axle]
