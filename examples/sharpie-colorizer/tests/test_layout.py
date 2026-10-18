"""The numbers behind the block, from params and the ruler measurements: grip, wear room, clearances."""
import math
from dataclasses import replace

import pytest

from sharpie_colorizer.layout import (base_t, channel_y, clip_strain, mouth_l, nose_reach, shoulder_from_tip,
                                      straight_from_tip, tip_point, tip_r, top_z, validate)
from sharpie_colorizer.params import P


def test_grip_and_wear_from_the_measurements():
    assert mouth_l(P) - straight_from_tip(P, "long") == pytest.approx(P.grip_min)
    assert shoulder_from_tip(P, "short") - mouth_l(P) - P.wear_max >= P.shoulder_gap_min
    assert mouth_l(P) - straight_from_tip(P, "short") >= P.grip_min  # more grip at the short reading


def test_nose_bore_leaves_the_far_half_of_the_channel():
    assert nose_reach(P) > -P.channel_d / 2 + 0.4


def test_validate_rejects_a_seated_shoulder_and_a_shallow_tilt():
    validate(P)
    with pytest.raises(ValueError, match="shoulder_to_felt_short"):
        validate(replace(P, shoulder_to_felt_short=P.front_straight_l + 2))
    with pytest.raises(ValueError, match="tilt_deg"):
        validate(replace(P, tilt_deg=30.0))


def test_outlet_tube_clears_the_clip_front_wall():
    assert channel_y(P) - P.tube_od / 2 > P.bar_w / 2 + P.clip_clear + P.clip_t


def test_tips_staggered_and_on_their_own_side():
    for i, phi in enumerate(P.azimuths_deg):
        x, y, z = tip_point(P, i)
        assert math.hypot(x, y - channel_y(P)) == pytest.approx(tip_r(P))
        assert math.degrees(math.atan2(y - channel_y(P), x)) % 360 == pytest.approx(phi % 360)
        assert z == pytest.approx(base_t(P) + P.tip_lift + i * P.stagger)


def test_clip_flex_stays_elastic_for_every_hook():
    assert all(clip_strain(P, h) <= 0.02 for h in P.hooks)


def test_heights_on_layers():
    assert P.printer.on_layer(base_t(P)) and P.printer.on_layer(top_z(P))
