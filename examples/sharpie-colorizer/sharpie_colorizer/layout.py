"""Pure numbers (no CAD): where each marker sits, how deep its socket grips, and the checks that the ruler
measurements still leave room. Block frame: X along the bar, Y toward the outlet side, z = 0 on the clip's top web;
the channel is vertical at (0, channel_y)."""
import math

from sharpie_colorizer.params import P, Params


def tip_r(p: Params = P) -> float:
    """Felt point's distance from the channel axis: inside the filament surface by felt_press."""
    return p.filament_d / 2 - p.felt_press


def axis(p: Params = P, i: int = 0) -> tuple[float, float, float]:
    """Unit vector of marker i, from its felt point up and out."""
    t, phi = math.radians(p.tilt_deg), math.radians(p.azimuths_deg[i])
    return math.sin(t) * math.cos(phi), math.sin(t) * math.sin(phi), math.cos(t)


def _s2f(p: Params, reading: str) -> float:
    return {"long": p.shoulder_to_felt_long, "short": p.shoulder_to_felt_short}[reading]


def straight_from_tip(p: Params = P, reading: str = "long") -> float:
    """Felt point to where the straight Ø11 section starts."""
    return p.felt_l + _s2f(p, reading) - p.front_straight_l


def shoulder_from_tip(p: Params = P, reading: str = "long") -> float:
    """Felt point to the Ø13 shoulder."""
    return p.felt_l + _s2f(p, reading)


def mouth_l(p: Params = P) -> float:
    """Felt point to the socket's mouth: grip_min of straight section in the socket at the long reading."""
    return straight_from_tip(p, "long") + p.grip_min


def fit_start_l(p: Params = P) -> float:
    """Where the Ø fit bore starts (behind the nose at the short reading, so the round-in never meets plastic)."""
    return p.felt_l + p.nose_l


def nose_start_l(p: Params = P) -> float:
    """Where the nose bore starts: low enough for the nose of a marker worn wear_max and pushed in."""
    return p.felt_l - p.wear_max - 0.5


def channel_y(p: Params = P) -> float:
    """Channel in front of the bar, so the outlet tube drops past the clip's front wall."""
    return p.bar_w / 2 + p.clip_clear + p.clip_t + p.tube_od / 2 + 1.0


def cone_h(p: Params = P) -> float:
    """45° step from a tube socket down to the channel."""
    return (p.tube_fit_d - p.channel_d) / 2


def base_t(p: Params = P) -> float:
    """Base under the markers: the rail slot, its 45° peaked roof, and a floor above the peak."""
    return p.printer.snap(p.rail_h + p.rail_clear + p.rail_head / 2 + p.rail_clear + p.floor_t)


def tip_point(p: Params = P, i: int = 0) -> tuple[float, float, float]:
    """Marker i's felt point, block frame."""
    phi = math.radians(p.azimuths_deg[i])
    return (tip_r(p) * math.cos(phi), channel_y(p) + tip_r(p) * math.sin(phi), base_t(p) + p.tip_lift + i * p.stagger)


def top_z(p: Params = P) -> float:
    """Top of the column: above the last felt, a stretch of channel, the inlet's cone and socket."""
    t = math.radians(p.tilt_deg)
    z = tip_point(p, len(p.azimuths_deg) - 1)[2] + p.felt_l * math.cos(t) + p.inlet_gap + cone_h(p) + p.tube_depth
    return p.printer.snap(z)


def boss_r(p: Params = P) -> float:
    return p.marker_fit_d / 2 + p.wall


def nose_reach(p: Params = P) -> float:
    """Signed distance of the nose bore's innermost edge from the channel axis, toward its own side. It may nick
    its own side of the channel but must leave the far half alone, so the opposite wall still guides."""
    t = math.radians(p.tilt_deg)
    return tip_r(p) + nose_start_l(p) * math.sin(t) - (p.nose_d / 2 + p.nose_clear) * math.cos(t)


def clip_strain(p: Params = P, hook: float = 2.0) -> float:
    """Peak strain in a clip wall bent outward by `hook` while snapping on (cantilever, fixed at the web)."""
    return 3 * p.clip_t * hook / (2 * (p.bar_h + 2 * p.clip_clear + p.clip_t) ** 2)


def validate(p: Params = P) -> None:
    """Raise with the value and the fix when the measurements don't leave room."""
    gap = shoulder_from_tip(p, "short") - mouth_l(p) - p.wear_max
    if gap < p.shoulder_gap_min:
        raise ValueError(f"shoulder_to_felt_short={p.shoulder_to_felt_short}: a worn marker's shoulder would be "
                         f"{gap:.1f} mm from the mouth (need {p.shoulder_gap_min}); lower grip_min or re-measure")
    if nose_reach(p) <= -p.channel_d / 2 + 0.4:
        raise ValueError(f"tilt_deg={p.tilt_deg}: the nose bore reaches {nose_reach(p):.2f} mm past the channel "
                         f"axis into the far wall; raise tilt_deg or measure nose_d")
    worst = max(p.hooks)
    if clip_strain(p, worst) > 0.02:
        raise ValueError(f"hooks={p.hooks}: the clip strains {clip_strain(p, worst):.3f} snapping on a {worst} mm "
                         f"hook (max 0.02); use a smaller hook or a thinner clip_t")
