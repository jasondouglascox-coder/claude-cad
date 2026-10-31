"""Fill the mat: rows of cats standing on a common baseline, each slid in until it's spacing from its neighbours."""
from functools import cache
from itertools import cycle

from shapely import affinity
from shapely.geometry import box

from . import cats
from .params import P

STEP = 0.05  # how finely cats slide together


def _slide(shape, placed, dx, dy, p):
    """Move shape by (dx, dy) steps for as long as it stays spacing clear of everything placed and on the mat."""
    while True:
        moved = affinity.translate(shape, dx, dy)
        x0, y0, _, _ = moved.bounds
        if x0 < p.margin - 1e-9 or y0 < p.margin - 1e-9:
            return shape
        if any(moved.distance(q) < p.spacing for q in placed):
            return shape
        shape = moved


@cache
def layout(p=P):
    """[(name, shape)] on the mat (inches, origin at its corner): the test square first, then the poses in turn."""
    square = box(0, 0, p.test_square, p.test_square)
    poses = [(n, cats.cat(n, p)) for n in cats.POSES]
    items = cycle(poses)
    queue = [("test_square", square)]
    top_limit = p.mat[1] - p.margin
    right_limit = p.mat[0] - p.margin
    placed = []
    y = p.margin
    while True:
        row, x = [], p.margin
        while True:
            name, s = queue.pop(0) if queue else next(items)
            s = affinity.translate(s, x, y)
            if s.bounds[2] > right_limit:
                queue.insert(0, (name, affinity.translate(s, -s.bounds[0], -s.bounds[1])))
                break
            s = _slide(s, [q for _, q in row], -STEP, 0, p)  # tuck in beside the last one
            row.append((name, s))
            x = s.bounds[2] + p.spacing
        # drop the row onto the ones below
        rows_below = [q for _, q in placed]
        shift = 0.0
        while all(affinity.translate(q, 0, shift - STEP).bounds[1] >= p.margin - 1e-9 for _, q in row) and not any(
                affinity.translate(q, 0, shift - STEP).distance(b) < p.spacing for _, q in row for b in rows_below):
            shift -= STEP
        row = [(n, affinity.translate(q, 0, shift)) for n, q in row]
        if max(q.bounds[3] for _, q in row) > top_limit:
            row = [(n, q) for n, q in row if q.bounds[3] <= top_limit]
            placed += row
            return tuple(placed)
        placed += row
        y = max(q.bounds[3] for _, q in row) + p.spacing
