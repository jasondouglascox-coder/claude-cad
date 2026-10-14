"""Pairwise interference for assembly tests: place every part, require intersection volume ~ 0."""
import itertools

from build123d import Shape


def boxes_overlap(a, b) -> bool:
    return not (a.max.X <= b.min.X or b.max.X <= a.min.X or a.max.Y <= b.min.Y or b.max.Y <= a.min.Y
                or a.max.Z <= b.min.Z or b.max.Z <= a.min.Z)


def find_clashes(items: list[tuple[str, Shape]], tol: float = 1e-3) -> list[tuple[str, str, float]]:
    """(name a, name b, shared volume) for every pair sharing more than tol mm^3. Touching faces don't count.
    Bounding boxes prefilter the pairs, since booleans are the slow part."""
    boxes = [(n, s, s.bounding_box()) for n, s in items]
    out = []
    for (na, a, ba), (nb, b, bb) in itertools.combinations(boxes, 2):
        if boxes_overlap(ba, bb):
            v = (a & b).volume
            if v > tol:
                out.append((na, nb, round(v, 4)))
    return out
