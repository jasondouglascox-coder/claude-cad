"""Pure math, no CAD: where every petal stands and how it's shaped, from params and the seed."""
import random
from dataclasses import dataclass

from peony_wall.params import Params

GOLD = 137.508  # golden angle (deg): each bowl petal turned this far from the last


@dataclass(frozen=True)
class Spec:
    kind: str  # guard, bowl or fold
    angle: float  # where it stands round the axis (deg)
    foot: float  # foot radius
    length: float  # along its side, foot to rim
    lean0: float  # lean at the foot (deg from upright; negative curls in)
    lean: float  # lean at the rim
    half: float  # half the angle it wraps round the axis at its rim (deg)
    bend: float  # how the lean grows along it (~ t ** bend)
    waves: float  # ruffle waves across it
    amp: float  # ruffle height at the rim
    cup: float  # cupped across it
    phase: float  # where the ruffle's waves start


def lerp(pair: tuple, f: float) -> float:
    return pair[0] + (pair[1] - pair[0]) * f


def specs(p: Params) -> list[Spec]:
    """Every petal: guards, then the bowl from innermost to outermost, then the folds. The random draws come in a
    fixed order from p.seed, so the flower is the same every build."""
    rng = random.Random(p.seed)
    u = lambda a, b: rng.uniform(a, b)
    jl, j0, jlen, jh = p.jitter
    out = []
    for i in range(p.guards):
        out.append(Spec("guard", i * 360 / p.guards + u(-p.guard_turn, p.guard_turn), p.guard_foot + u(-3, 3),
                        p.guard_length + u(-3, 3), p.guard_lean[0], min(p.guard_lean[1] + u(-3, 3), p.lean_out_max),
                        p.guard_half + u(-3, 3), 0.9, u(*p.waves), u(*p.guard_amp), 0.0, u(0, 6.28)))
    for i in range(p.bowl):
        f = i / (p.bowl - 1)
        foot = p.bowl_feet[0] + (p.bowl_feet[1] - p.bowl_feet[0]) * f ** 0.85
        length, lean, half = lerp(p.bowl_length, f) + u(-jlen, jlen), lerp(p.bowl_lean, f) + u(-jl, jl), \
            lerp(p.bowl_half, f) + u(-jh, jh)
        lean0 = lerp(p.bowl_lean0, f) + u(-j0, j0)
        out.append(Spec("bowl", i * GOLD, foot, length, lean0, max(lean, -p.lean_in_max), half, 1.1, u(*p.waves),
                        u(*p.bowl_amp), u(*p.bowl_cup), u(0, 6.28)))
    for a in p.folds:
        out.append(Spec("fold", a, p.fold_foot, p.fold_length, p.fold_lean[0], max(p.fold_lean[1], -p.lean_in_max),
                        p.fold_half, 1.0, 2.5, 1.8, 2.0, u(0, 6.28)))
    return out
