"""2D profile helpers. Flat-printed parts are profiles extruded to a thickness, so most geometry starts here."""
import math

from build123d import Align, Cone, Cylinder, Helix, Kind, Part, Plane, Polygon, Pos, Rectangle, Sketch, offset, sweep


def poly(*pts: tuple) -> Sketch:
    """Polygon traced counter-clockwise whatever order the points come in, so it extrudes toward +Z.
    (A clockwise Polygon extrudes toward -Z and the part silently splits into several solids.)"""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return Polygon(*(pts if area > 0 else pts[::-1]), align=None)


def rect(u0: float, u1: float, v0: float, v1: float) -> Sketch:
    """Axis-aligned rectangle from corner (u0, v0) to (u1, v1)."""
    return Pos(u0, v0) * Rectangle(u1 - u0, v1 - v0, align=(Align.MIN, Align.MIN))


def grow(s: Sketch, clearance: float) -> Sketch:
    """Grow a profile by a fit clearance, keeping sharp corners."""
    return offset(s, clearance, kind=Kind.INTERSECTION) if clearance else s


def bowtie(length: float, head: float, waist: float, clearance: float = 0.0) -> Sketch:
    """Bow-tie (butterfly) key: waist on the joint line x = 0, heads at x = ±length/2. Locks two flat parts
    edge to edge; cut the socket with clearance > 0."""
    hl, hh, hw = length / 2, head / 2, waist / 2
    return grow(poly((-hl, -hh), (0, -hw), (hl, -hh), (hl, hh), (0, hw), (-hl, hh)), clearance)


def dovetail(x: float, y: float, neck: float, head: float, length: float, clearance: float = 0.0) -> Sketch:
    """Jigsaw tab with its neck on x, widening toward +x. Joins long flat parts end to end."""
    n, h = neck / 2, head / 2
    return grow(poly((x - 0.01, y - n), (x + length, y - h), (x + length, y + h), (x - 0.01, y + n)), clearance)


def pencil_hole(throat_d: float, throat_h: float, t: float, sink_deg: float = 30.0) -> Part:
    """Hole through a flat part t thick, to cut at each mark: a throat throat_d across at the bottom (the bed side,
    against the work) where a pencil point or a nail comes through on the mark, and a cone above it, sink_deg off
    vertical, guiding the point down to it. Centred on the origin, a hair past both faces."""
    top = throat_d / 2 + (t - throat_h + 0.01) * math.tan(math.radians(sink_deg))
    throat = Cylinder(throat_d / 2, throat_h + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cone = Pos(0, 0, throat_h) * Cone(throat_d / 2, top, t - throat_h + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return Pos(0, 0, -0.005) * (throat + cone)


def thread(radius: float, depth: float, pitch: float, length: float, crest: float = 0.5, inward: bool = False,
           z0: float = 0.0, overlap: float = 0.3, flank: float = 40.0) -> Part:
    """Right-hand helical ridge with flanks `flank` degrees off the axis, to fuse onto a tube: it prints upright
    without support, inside or out (the sweep tilts the profile by the helix angle, so 45 lands just past 45°). It stands on the tube wall at `radius` and reaches `depth` out (or in, for a nut); its center line passes
    angle 0 (+X) at z0 and rises `pitch` per turn for `length`. `overlap` sinks the root into the wall so the union
    fuses. Mate a bolt half a pitch out of phase with its nut, its crest a radial clearance inside the nut's root."""
    run = 1 / math.tan(math.radians(flank))  # axial run per mm of depth
    half_base = crest / 2 + depth * run
    if 2 * half_base >= pitch:
        raise ValueError(f"thread: crest {crest} + 2 x depth {depth} with {flank}° flanks must fit in the pitch {pitch}")
    s = -1 if inward else 1
    sunk = half_base + overlap * run  # the flanks carry on into the wall: no flat underside anywhere
    pts = [(radius - s * overlap, -sunk), (radius + s * depth, -crest / 2), (radius + s * depth, crest / 2),
           (radius - s * overlap, sunk)]
    ridge = sweep(Plane.XZ * Polygon(*pts, align=None), Helix(pitch, length, radius), is_frenet=True)
    return Pos(0, 0, z0) * Part(ridge.solids())


def thread_gap(depth: float, pitch: float, crest: float, clearance: float, flank: float = 40.0) -> float:
    """Axial play on each flank between a bolt and nut from thread(), the bolt's crest `clearance` inside the nut's
    root. Check fits with this (and is_inside sampling), not by intersecting the two ridges: OCC booleans between
    swept helices come back empty at random, even for ridges fully in phase."""
    run = 1 / math.tan(math.radians(flank))
    return (pitch - 2 * crest - 2 * run * (depth - clearance)) / 2
