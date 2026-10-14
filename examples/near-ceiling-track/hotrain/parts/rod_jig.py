"""Bending jig: two stacked convex arcs. Bend the outer rod against the bottom step and the inner rod
against the top step, sliding the rod along as you go."""
import math

from build123d import Part, Pos, Sketch, extrude

from hotrain.joints import poly
from hotrain.params import P, Params

STEP_H = 8.0
WIDTH = 25.0


def _sector(r_in: float, r_out: float, half_angle: float) -> Sketch:
    pts = []
    for i in range(25):
        a = -half_angle + 2 * half_angle * i / 24
        pts.append((r_out * math.sin(a), r_out * math.cos(a)))
    for i in range(25):
        a = half_angle - 2 * half_angle * i / 24
        pts.append((r_in * math.sin(a), r_in * math.cos(a)))
    return poly(*pts)


def make(p: Params = P) -> Part:
    r_outer = p.curve_r + p.rod_y - p.rod_d / 2  # rod inner surface radius
    r_inner = p.curve_r - p.rod_y - p.rod_d / 2
    chord = p.bed_usable - 6
    half = math.asin(chord / 2 / r_outer)
    low = extrude(_sector(r_inner - WIDTH, r_outer, half), STEP_H)
    high = Pos(0, 0, STEP_H) * extrude(_sector(r_inner - WIDTH, r_inner, half), STEP_H)
    j = low + high
    bb = j.bounding_box()
    return Pos(-bb.min.X, -bb.min.Y, 0) * j
