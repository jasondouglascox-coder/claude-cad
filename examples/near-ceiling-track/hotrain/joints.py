"""This project's joints, sized from params. Generic profiles (rect, poly, bowtie, dovetail) live in cadkit.shapes."""
from build123d import Sketch

from cadkit.shapes import bowtie, dovetail, poly, rect  # noqa: F401  (re-exported for the parts)
from hotrain.params import Params


def butterfly(p: Params, clearance: float = 0.0) -> Sketch:
    """Bow-tie key: waist on the joint line (x=0), heads at x = ±key_len/2. clearance grows it."""
    return bowtie(p.key_len, p.key_head, p.key_waist, clearance)


def jigsaw(p: Params, x: float, y: float, clearance: float = 0.0) -> Sketch:
    """Dovetail tab whose neck sits on x and widens toward +x (into the next ladder)."""
    return dovetail(x, y, p.jig_neck, p.jig_head, p.jig_len, clearance)
