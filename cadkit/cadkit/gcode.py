"""What a sliced plate prints, read from its G-code: every extruding move as a straight segment, with its layer and
the slicer's feature name (`; FEATURE: Support`, as Bambu Studio, OrcaSlicer and PrusaSlicer label them). For
checking a slice against the design, e.g. that no support lands inside a keyhole."""
import math
import re

_NUM = re.compile(r"([XYZEIJ])(-?[\d.]+)")
ARC_STEP = 0.3  # mm: arcs (G2/G3) come back as chords about this long


# not part of the printed object: what a centre of mass leaves out
NOT_THE_PART = ("Prime tower", "Support", "Support interface", "Support transition", "Brim", "Skirt", "Custom")


def extrusions(text: str) -> list[tuple[float, float, float, float, float, str]]:
    """[(x0, y0, x1, y1, layer z, feature)] for every move that extrudes (E > 0), arcs split into chords."""
    return [m[:6] for m in _moves(text)]


def centre_of_mass(text: str, skip: tuple[str, ...] = NOT_THE_PART) -> tuple[float, float, float]:
    """Where the printed part balances: each extruding move's midpoint weighed by its E (what it lays down), moves
    in the `skip` features left out."""
    w = sx = sy = sz = 0.0
    for x0, y0, x1, y1, z, feature, e in _moves(text):
        if feature not in skip:
            w, sx, sy, sz = w + e, sx + e * (x0 + x1) / 2, sy + e * (y0 + y1) / 2, sz + e * z
    return sx / w, sy / w, sz / w


def _moves(text: str) -> list[tuple[float, float, float, float, float, str, float]]:
    """extrusions, each with its E (an arc's shared out over its chords)."""
    out, x, y, z, feature = [], 0.0, 0.0, 0.0, ""
    for line in text.splitlines():
        if line.startswith(";"):
            if line.startswith("; FEATURE:"):
                feature = line.split(":", 1)[1].strip()
            elif line.startswith("; Z_HEIGHT:"):
                z = float(line.split(":", 1)[1])
            continue
        cmd = line[:3]
        if cmd not in ("G0 ", "G1 ", "G2 ", "G3 "):
            continue
        d = {k: float(v) for k, v in _NUM.findall(line.split(";")[0])}
        nx, ny = d.get("X", x), d.get("Y", y)
        if d.get("E", 0.0) > 0 and (nx, ny) != (x, y):
            if cmd in ("G2 ", "G3 ") and ("I" in d or "J" in d):
                cx, cy = x + d.get("I", 0.0), y + d.get("J", 0.0)
                r = math.hypot(x - cx, y - cy)
                a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
                if cmd == "G3 ":  # counter-clockwise
                    while a1 <= a0:
                        a1 += 2 * math.pi
                else:
                    while a1 >= a0:
                        a1 -= 2 * math.pi
                n = max(2, math.ceil(abs(a1 - a0) * r / ARC_STEP))
                px, py = x, y
                for k in range(1, n + 1):
                    t = a0 + (a1 - a0) * k / n
                    qx, qy = (nx, ny) if k == n else (cx + r * math.cos(t), cy + r * math.sin(t))
                    out.append((px, py, qx, qy, z, feature, d["E"] / n))
                    px, py = qx, qy
            else:
                out.append((x, y, nx, ny, z, feature, d["E"]))
        x, y = nx, ny
    return out
