"""Both halves in PRINT orientation: outer face on the bed, centered at center(p). The *_centered versions sit on
the spool axis (Z) for the assembly."""
import math

from build123d import Align, Box, Cylinder, Part, Pos, Rot

from cadkit.shapes import thread, thread_gap
from refill_spool.params import P, Params

UP = (Align.CENTER, Align.CENTER, Align.MIN)
OUT = (Align.MIN, Align.CENTER, Align.MIN)  # a box reaching out along +X from its position


def center(p: Params = P) -> tuple[float, float]:
    return p.rim_d / 2, p.rim_d / 2


def ring(r0: float, r1: float, h: float) -> Part:
    return Cylinder(r1, h, align=UP) - Cylinder(r0, h, align=UP)


def radial_box(angle: float, r0: float, r1: float, w: float, h: float, z: float = 0.0) -> Part:
    """A box from radius r0 to r1 along `angle` degrees, w wide, from z up h."""
    return Rot(0, 0, angle) * Pos(r0, 0, z) * Box(r1 - r0, w, h, align=OUT)


def flange(p: Params, strap_gaps: bool = False) -> Part:
    """Rim, middle ring and spokes, flange_t thick. Each spoke reaches from just inside the bore to the middle of the
    rim. strap_gaps: open the middle ring where each strap crosses the flange's outer face."""
    f = ring(p.rim_in, p.rim_d / 2, p.flange_t)
    mid = ring(p.mid_ring_d / 2 - p.mid_ring_w / 2, p.mid_ring_d / 2 + p.mid_ring_w / 2, p.flange_t)
    if strap_gaps:
        for a in p.strap_angles():
            mid -= radial_box(a, p.mid_ring_d / 2 - p.mid_ring_w, p.mid_ring_d / 2 + p.mid_ring_w, p.mid_ring_gap,
                              p.flange_t + 1, -0.5)
    f += mid
    for a in p.spoke_angles():
        f += radial_box(a, p.bore_d / 2 + 0.5, p.rim_in + p.rim_w / 2, p.spoke_w, p.flange_t)
    return f


def run(p: Params) -> float:
    """Axial run of a thread flank per mm of depth."""
    return 1 / math.tan(math.radians(p.thread_flank))


def sunk(p: Params) -> float:
    """Half the ridge's height where it sinks into the wall (cadkit.shapes.thread, overlap 0.3)."""
    return p.thread_crest / 2 + (p.thread_depth + 0.3) * run(p)


def nut_span(p: Params) -> tuple[float, float]:
    """Heights of the nut ridge's center line where it starts (at angle 0) and ends: whole inside the thread band.
    Ridges aren't clipped to their band: OCC intersections of a swept ridge come back empty at random."""
    return p.barrel_top - p.thread_len + sunk(p), p.barrel_top - sunk(p)


def bolt_span(p: Params) -> tuple[float, float]:
    """The cap ridge's start (at angle 0) and end, in the cap's print frame. Screwed home, the cap is flipped over
    the barrel (angle -> -angle, z -> width - z) and its ridge sits half a pitch from the nut's, pulled up against
    the nut ridge above by the flank play: that's what holds the flange down on the barrel top, and it clocks the
    cap's spokes to the model's angles. The ridge starts at the first such phase above the flange."""
    play = play_per_flank(p) - 0.02
    z = (p.width - nut_span(p)[0] - p.pitch / 2 - play) % p.pitch
    lo = p.flange_t + sunk(p)
    return z + p.pitch * math.ceil((lo - z) / p.pitch), p.flange_t + p.thread_len - sunk(p)


def play_per_flank(p: Params) -> float:
    return thread_gap(p.thread_depth, p.pitch, p.thread_crest, p.thread_clear, p.thread_flank)


def engaged(p: Params) -> float:
    """Height over which both ridges run, screwed home."""
    n0, n1 = nut_span(p)
    b0, b1 = bolt_span(p)
    return min(n1, p.width - b0) - max(n0, p.width - b1)


def barrel_half_centered(p: Params = P) -> Part:
    top = p.barrel_top
    part = flange(p, strap_gaps=True) + ring(p.bore_d / 2, p.barrel_d / 2, p.flange_t)  # solid floor under barrel
    part += ring(p.bore_d / 2, p.bore_d / 2 + p.bore_wall, top)  # the cap's flange lands on its end
    part += ring(p.nut_root, p.barrel_d / 2, top)
    z0, z1 = nut_span(p)
    part += thread(p.nut_root, p.thread_depth, p.pitch, z1 - z0, p.thread_crest, inward=True, z0=z0,
                   flank=p.thread_flank)
    for a in p.strap_angles():
        part -= radial_box(a, p.track_floor, p.barrel_d / 2 + 0.5, p.strap_w, top + 1, -0.5)  # strap track
    part += radial_box(p.key_angle, p.barrel_d / 2 - 0.3, p.barrel_d / 2 + p.key_h, p.key_w, p.flange_t + p.key_len)
    part = Part(part.solids())
    part.label = "barrel_half"
    return part


def cap_centered(p: Params = P) -> Part:
    top = p.flange_t + p.thread_len
    inner = p.bolt_root - p.spigot_wall
    part = flange(p) + ring(p.bore_d / 2, p.barrel_d / 2, p.flange_t)  # solid from the bore over the barrel's top
    part += ring(inner, p.bolt_root, top)
    z0, z1 = bolt_span(p)
    part += thread(p.bolt_root, p.thread_depth, p.pitch, z1 - z0, p.thread_crest, z0=z0, flank=p.thread_flank)
    part = Part(part.solids())
    part.label = "cap"
    return part


def barrel_half(p: Params = P) -> Part:
    part = Pos(*center(p), 0) * barrel_half_centered(p)
    part.label = "barrel_half"
    return part


def cap(p: Params = P) -> Part:
    part = Pos(*center(p), 0) * cap_centered(p)
    part.label = "cap"
    return part
