"""Every dimension in one place (inches: the Cameo's mat is 24 x 24). Tests derive from these.

Each cat is one solid black silhouette: the blade cuts its outline, the vinyl inside stays. Poses are drawn on a
100-unit grid (y up) in cats.py and scaled so the longer side is cat_size."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Params:
    cat_size: float = 3.0  # longer side of each cat
    min_feature: float = 0.125  # no leg, tail or ear tip narrower: thinner vinyl tears when weeding
    min_gap: float = 0.1  # holes (between legs, inside a tail curl) at least this wide to weed
    min_hole_area: float = 0.03  # smaller holes are a chore to pick out

    mat: tuple = (24.0, 24.0)  # Cameo Pro mat
    margin: float = 0.5  # clear of the mat's edges
    spacing: float = 0.5  # between cats: room to weed, cut apart and select each one in Studio
    test_square: float = 1.0  # measure it after importing: Studio guesses a DXF's units


P = Params()
