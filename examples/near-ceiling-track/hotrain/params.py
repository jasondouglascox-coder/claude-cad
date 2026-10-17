"""Every dimension in the project. Units: millimetres. Parts read these; nothing else hard-codes a size."""
from dataclasses import dataclass, field

from cadkit import Printer
from cadkit.settings import settings

INCH = 25.4


@dataclass(frozen=True)
class Params:
    # track (NMRA HO). Rail: Walthers 948-10000 Code 100 nickel silver; Walthers doesn't publish its profile, so
    # these are NMRA RP-15.1 nominals for Code 100. Check with calipers when it arrives.
    gauge: float = 16.6
    rail_height: float = 0.100 * INCH  # A
    rail_base_w: float = 0.090 * INCH  # B
    rail_head_w: float = 0.045 * INCH  # C
    rail_base_edge: float = 0.018 * INCH  # D: base thickness at its edge
    rail_head_depth: float = 0.023 * INCH  # H
    rail_base_slope: float = 15.0  # degrees: base top rises from the edge toward the web
    track_offset: float = 1.75 * INCH  # wall to track centerline (room for the corner bowstrings)
    car_half_w: float = 20.0  # widest HO car body half-width, for wall clearance
    car_sill_h: float = 12.0  # car body underside above the rail top (~3.5 scale ft), for the tip check
    car_body_h: float = 41.0  # car body height above its sill
    flange_depth_max: float = 1.6  # deep vintage (pizza-cutter) flange plus print tolerance
    rail_top_below_ceiling: float = 12 * INCH

    # bridge ties
    tie_l: float = 35.0
    tie_w: float = 2.6
    tie_h: float = 2.4  # layer multiple (0.2): the brown/gray seam and every top land on a layer boundary
    tie_pitch: float = 5.5  # nominal; each bay adjusts slightly to fit a whole number of ties
    tie_plate_h: float = 0.4
    shoulder_h: float = 0.6
    shoulder_w: float = 0.8
    spike_lip_every: int = 4
    spike_lip_overhang: float = 0.3
    spike_lip_t: float = 0.4
    long_tie_every: int = 4  # handrail post spacing in ties; bays hold a multiple of this
    solder_feed_w: float = 1.6  # feeder groove straight across under both rails, in the gap's first opening
    solder_feed_floor: float = 0.8  # floor under the feeder groove: keeps both runners, and so the ladder, in one piece
    solder_gap: bool = True  # solder gap at each bay's mid: the plain ties between the two handrail posts nearest mid
    solder_room_stub: float = 2.8  # room side keeps this much of each left-out tie's end, so it still reads from the room
    solder_bar_h: float = 1.0  # bar on top of the room-side tie ends (flush with the tie tops) that holds the stubs
    solder_bar_inset: float = 0.8  # bar sits this far back from the tie end faces
    long_tie_reach: float = 28.0  # track center to room-side end of a long tie
    socket_pad: float = 4.4
    runner_w: float = 5.6
    jig_neck: float = 2.4
    jig_head: float = 3.6
    jig_len: float = 2.0

    # straight-run style: "arch" (open-spandrel arches) or "deck_truss" (Warren deck truss between piers)
    run_style: str = "arch"

    # arch panels
    panel_t: float = 3.2
    pier_depth: float = 3 * INCH  # below tie underside
    crown_depth: float = 1 * INCH  # below tie underside
    top_band_h: float = 6.0
    rib_h: float = 6.0
    post_w: float = 3.0
    post_pitch: float = 2 * INCH
    pier_w: float = 1.25 * INCH  # full pier; each bay owns half
    crown_block_w: float = 7.0
    tab_len: float = 6.0
    # deck truss panels (run_style="deck_truss"); pier, top band, tabs, bracket and latch are shared
    dt_depth: float = 2.25 * INCH  # bottom chord underside below the tie underside (~16 scale ft)
    dt_chord_h: float = 5.0
    dt_post_w: float = 4.5  # inclined end post
    dt_diag_w: float = 2.4
    dt_vert_w: float = 2.0
    dt_mid_w: float = 2.5  # each half's share of the mid-bay post
    dt_gusset_w: float = 7.0  # each half's share of the bottom-chord splice plate
    dt_gusset_h: float = 12.0
    dt_key_len: float = 8.0  # small bow-tie in the splice plate
    dt_key_head: float = 8.0
    dt_key_waist: float = 4.5
    dt_lap: float = 1.0  # members overlap so joints are areas (3MF-safe)
    pier_cap_h: float = 4.0  # concrete-look pier: ledge under the top chord
    pier_cap_out: float = 1.5
    pier_batter: float = 2.5  # pier face flares out this much at the bottom
    cf_x_w: float = 1.6  # cross-frame sway-brace bar width
    tab_first: float = 1 * INCH
    tab_pitch: float = 2 * INCH
    tab_joint_keepout: float = 8.0
    bay_len: float = 16 * INCH
    min_bay_len: float = 8 * INCH
    max_bay_len: float = 480.0  # half bay + one tie pitch + jigsaw tab must fit bed_usable

    # keystone (butterfly key at the crown)
    key_len: float = 12.0
    key_waist: float = 8.0
    key_head: float = 14.0

    # cross-frames
    cf_t: float = 2.4
    cf_wall: float = 2.5
    cf_bar: float = 3.0
    cf_border: float = 2.5
    rib_notch: float = 1.0

    # bus wires (two 16 AWG) along the wall, carried on cross-frame fingers
    bus_floor: float = -4.0  # Z of the cradle floor (tie underside = 0)
    finger_h: float = 2.0
    finger_lip_w: float = 1.2
    finger_lip_top: float = -1.0
    bus_notch_w: float = 7.8  # pass-through in the bracket web, in front of the flange

    # bracket
    bracket_t: float = 6.0
    bracket_member: float = 5.0
    bracket_bar: float = 4.0
    deck_block_margin: float = 6.0
    pier_notch: float = 1.5 * INCH  # half-lap: panels notched half the pier depth from the bottom, bracket slots come down the other half
    flange_w: float = 26.0
    bracket_open_min: float = 30.0  # shorter arm than this is printed as a solid web
    flange_t: float = 6.0
    screw_d: float = 4.6  # #8 screws, into studs or self-drilling drywall anchors
    screw_travel: float = 0.25 * INCH  # ± vertical adjustment
    screw_zs: tuple = (15.0, 65.0)  # below tie underside
    latch_top: float = 8.5  # below tie underside
    latch_win_h: float = 3.0
    latch_engage: float = 0.8
    latch_finger_w: float = 2.0
    latch_relief: float = 1.0
    latch_finger_len: float = 40.0

    # handrail
    handrail_h: float = 19.0  # above rail top
    dt_handrail_h: float = 12.0  # deck truss: short single-bar walkway railing (~3.5 scale ft)
    handrail_offset: float = 25.0  # track center to handrail centerline
    handrail_t: float = 1.6
    handrail_post_w: float = 2.0
    handrail_bar: float = 1.6
    peg_w: float = 1.6
    handrail_gap: float = 0.5

    # corners: bowstring spans on two aluminum rods
    alcove_w: float = 43.75 * INCH  # top wall to bump-out face; sets the one curve radius
    curve_spans: int = 5  # 18 degrees each
    bow_frame_y: float = 31.5  # frame centerline from the span's center line
    bow_frame_t: float = 3.2
    bow_chord_h: float = 5.0  # bottom chord (tie girder) height above the ties' underside
    bow_rise: float = 38.0  # arch crown above the rail top
    bow_rib_w: float = 3.0
    bow_panels: int = 6
    bow_hanger_w: float = 1.6
    bow_post_w: float = 4.0
    bow_edge_w: float = 6.0  # (legacy) deck edge beam width; frames now hug the deck in a U instead
    frame_ledge: float = 2.5  # corner frames: inward ledges above/below the tie band form a U the tie ends slide into
    frame_ledge_lo: float = 1.6  # ledge under the ties
    frame_ledge_hi: float = 1.2  # ledge over the ties
    frame_ledge_end: float = 3.6  # lower ledge stops this short of each frame end (clears the floor beams)
    corner_style: str = "pony"  # side frames: "pony" (Pratt pony truss) or "bowstring"
    truss_rise: float = 42.0  # pony truss top chord top above the rail top
    truss_panels: int = 6  # first and last panels are the inclined end posts
    truss_chord_w: float = 3.5  # top chord depth
    truss_post_w: float = 4.0  # inclined end post width (perpendicular to its slope)
    truss_vert_w: float = 2.2
    truss_diag_w: float = 2.0
    truss_gusset: float = 2.5  # triangular gusset legs at web-to-chord joints
    bow_tab_len: float = 8.0
    rod_d: float = 6.35  # 1/4" aluminum
    rod_y: float = 18.0  # rod centerlines from track center
    rod_cover: float = -0.8  # negative: the rods' tops sit this deep in part-circle grooves under the corner ties
    rod_wall: float = 1.8
    rod_mouth: float = 0.24  # snap mouth: runner bottom this many rod diameters below the bore center (mouth ~0.88 d)
    rod_tail: float = 12.0  # rod runs this far past each end anchor
    fit_thread: float = 0.6  # loose bores that slide along hand-bent rods
    fb_t: float = 6.0  # floor beam thickness along the track
    fb_drop: float = 6.0  # floor beam depth below the runners
    bus_hook_drop: float = 11.0  # bus hook bottom below the beam bottom: wire passes under the deep brackets' 5 mm arm
    fb_reach: float = 10.0  # floor beam beyond the frames (cable eyes)
    cable_d: float = 2.5
    # ceiling anchor + 50 lb braided line (bridge corner), wrapped around tie ends outside a truss
    line_d: float = 0.5
    line_inset: float = 12.0  # wrap point past the portal, into the span
    anchor_screw_d: float = 3.8  # #6 pan-head wood screw clearance
    cleat_base_l: float = 42.0  # horn cleat, printed on its side (profile = side view, extruded cleat_w)
    cleat_screw_off: float = 17.0  # screws this far either side of center, outside the horns
    cleat_w: float = 7.0
    cleat_base_h: float = 2.5
    cleat_stem_l: float = 7.0
    cleat_horn_l: float = 26.0
    cleat_top: float = 6.5  # installed height below the ceiling
    cleat_jam: float = 0.7  # gap under a horn at the stem: braid jams here
    cleat_tip_gap: float = 2.0  # gap under a horn at its tip: line goes in here
    cleat_horn_tip: float = 1.8  # horn thickness at the tip
    portal_gap: float = 0.4
    deep_reach_margin: float = 12.0

    # stainless wire rail on a printed web: the curve test piece (docs/specs/2026-10-16-wire-rail-design.md).
    # Wire equators sit `gauge` apart; the wire top is rail_top.
    wire_d: float = 0.0508 * INCH  # 16 AWG 304 stainless (1.29 mm): set from caliper readings along the spool
    wire_seat_fit: float = 0.05  # cradle radius over the wire's: slides in, glued
    wire_base_w: float = 0.100 * INCH  # web foot on the runner
    wire_lip_w: float = 0.9  # field lip top: two nozzle lines (Bambu's classic walls drop a one-line wall)
    wire_step_gap: float = 0.05  # the gauge-side step under the wire stays this far inside the gauge face
    tread_keepout: float = 0.008 * INCH  # under the tread nothing but wire within this of the wire top
    wheel_n: float = 0.110 * INCH  # RP-25 Code 110 tire width
    wheel_t: float = 0.030 * INCH  # RP-25 flange width at the gaging point
    wheel_p: float = 0.010 * INCH  # RP-25 gaging point below the tread
    wheel_d_rp25: float = 0.025 * INCH  # RP-25 Code 110 flange depth
    wheel_b: float = 0.573 * INCH  # NMRA S-4.2 (Jun 2026) HO back-to-back target
    wheel_dia: float = 33 / 87.1 * INCH  # 33" freight wheel
    wheel_taper: float = 3.0  # degrees
    axle_d: float = 0.088 * INCH
    axle_l: float = 1.010 * INCH
    wire_layer: float = 0.08  # the gray web needs fine layers; the test plates' slicer settings carry these
    wire_first_layer: float = 0.16  # 0.16 + 28 x 0.08 = tie_h: the brown/gray seam stays on a layer
    wire_test_deg: float = 18.0  # one corner span; wire_test_pieces of them make the 90 degree corner
    wire_test_pieces: int = 5

    # fits
    fit_slide: float = 0.20
    fit_snap: float = 0.05

    # printer: yours, from cadkit.settings (CADKIT_BED... or cadkit.toml); with nothing set, the A1's 256 x 256 mm.
    # Half spans and ladders are sized to fit bed_usable; a smaller bed fails the fit tests with the numbers.
    bed: float = field(default_factory=lambda: settings().bed_x)
    bed_y: float = field(default_factory=lambda: settings().bed_y)
    bed_margin: float = field(default_factory=lambda: settings().margin)
    # Bambu Studio filament per print color (the plate 3MFs assign them per part). The user's AMS: 1 gray PETG,
    # 2 brown PETG; the white PLA for the ceiling cleats goes in 3 when they print.
    filament_gray: int = 1
    filament_brown: int = 2
    filament_white: int = 3

    @property
    def rail_ctc(self) -> float:
        return self.gauge + self.rail_head_w

    @property
    def rail_ys(self) -> tuple:
        return (-self.rail_ctc / 2, self.rail_ctc / 2)

    @property
    def rail_top(self) -> float:
        """Rail top above the tie underside (Z=0)."""
        return self.tie_h + self.tie_plate_h + self.rail_height

    @property
    def groove_w(self) -> float:
        return self.rail_base_w + self.fit_slide

    @property
    def curve_r(self) -> float:
        """Track radius on every corner: 1 + 3 straight spans of chord length exactly fill the alcove."""
        import math
        return (self.alcove_w - self.track_offset) / (1 + 6 * math.sin(math.radians(9)))

    @property
    def bow_span(self) -> float:
        import math
        return 2 * self.curve_r * math.sin(math.radians(90 / self.curve_spans / 2))

    @property
    def rod_zc(self) -> float:
        """Rod centerline height (tie underside = 0)."""
        return -(self.rod_d + self.fit_slide) / 2 - self.rod_cover

    @property
    def runner_bot(self) -> float:
        return self.rod_zc - self.rod_mouth * self.rod_d

    @property
    def bracket_depth(self) -> float:
        return self.pier_depth + self.bracket_bar

    @property
    def bed_usable(self) -> float:
        """The usable square: the shorter side."""
        return min(self.bed, self.bed_y) - self.bed_margin

    @property
    def printer(self) -> Printer:
        return Printer(bed=self.bed, bed_y=None if self.bed_y == self.bed else self.bed_y, margin=self.bed_margin)


P = Params()
