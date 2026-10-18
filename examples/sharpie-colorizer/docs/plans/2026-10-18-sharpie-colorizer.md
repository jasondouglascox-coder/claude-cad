# Sharpie Colorizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An inline Sharpie colorizer for the A1's external-spool guide tube. It's a black two-part print, a snap
clip for the 40 × 20 top frame bar plus a marker block that slides onto the clip. The block holds three press-fit
Sharpie Fine Points at an angle, with their felt tips on the filament. A fit-test plate prints first.

**Architecture:** Pure numbers go in `layout.py`: marker axes, tip points, mouth distance, channel offset, and
validation. Shared cutters and profiles go in `joints.py`: marker cavity, tube socket, rail and clip profiles. Three
part modules (`parts/clip.py`, `parts/block.py`, `parts/fittest.py`) each `make(p)` in print orientation and
`place(p)` into the use frame. `assembly.py` places the bar, clip, block, markers and tube paths for clash and
keep-out tests. `plates.py` and `build.py` write STEP, 3MF plates and renders. A new generic check,
`cadkit.checks.overhangs`, goes into cadkit.

**Tech Stack:** Python 3.12 (uv), build123d 0.13.0, cadkit (path dependency), pytest + xdist.

**Spec:** `examples/sharpie-colorizer/docs/specs/2026-10-18-sharpie-colorizer-design.md`. The marker numbers are in
`docs/measurements.md`.

## Global Constraints

- Units are mm. Every dimension lives in `sharpie_colorizer/params.py`. Tests derive expectations from `P`, with no
  magic numbers.
- **Use frame** (assembly): X runs along the bar. The bar's cross-section is centered on Y = Z = 0 (Y ±20 front
  and back, Z ±10). +Y is the outlet side, toward the head. The clip and block are symmetric front to back, so the
  user turns them around to send the outlet the other way. **Block frame** = use frame shifted so z = 0 is the
  clip's top web (the block's bottom face).
- Filament channel: vertical, at (X = 0, Y = `channel_y`), straight from the block's bottom to its top. Tube in at
  the top, tube out at the bottom.
- Markers: 3 of them, at azimuths 270° (back, over the bar), 30° and 150° around the channel. Each is tilted
  `tilt_deg` = 42° from vertical, with the felt pointing down. They're staggered `stagger` = 8 mm apart in height,
  lowest first in that order. Each felt tip point sits `felt_press` = 0.3 mm inside the filament surface on its own
  side.
- Press fit: the socket grips only the straight Ø11 front section, with at least `grip_min` = 12 mm of grip at the
  long length reading (the spec asks for 12–15). A worn felt gets pushed in by up to `wear_max` = 1 mm. Even then,
  at the short reading, the Ø13 shoulder stays at least `shoulder_gap_min` = 3 mm out from the mouth. Felt wear past
  `wear_max` brings the plastic nose onto the filament, which means it's time for a new marker.
- Every printed part is one valid solid, flat on Z = 0, watertight, with tops on layers (`printable_problems`,
  `open_edges`, `off_layer_z`). Nothing faces straight down (`downward_faces == []`) or overhangs more than 45°
  from vertical (`overhangs == []`). No supports.
- Nothing below `Z = −bar_h/2 − clip_clear − clip_t` in the use frame. That's the X gantry's space at max Z.
- One color: black, AMS slot 3 (`filament_black = 3`). No color changes.
- Unions must overlap (edge-to-edge unions mesh badly). 2D outlines go through `cadkit.shapes.poly`.
- Tests: `uv run pytest -n 4 -m "not slow"`. Commit after each task, ending with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Push to main is fine.

## Review Focus

1. **Loading new filament with all three markers in.** The cut end must get past the felt that sticks into the
   channel, guided by an unbroken opposite wall. `test_opposite_wall_guides_past_every_window`.
2. **Both length readings (32 vs 28.5 shoulder-to-felt).** At either one, nothing but felt reaches the filament,
   and the shoulder never seats. `test_markers_clear_block[long|short]`.
3. **A worn felt pushed deeper.** A felt worn by `wear_max` and pushed in until it touches again still clears the
   block, the other markers and (the nose) the filament. `test_markers_clear_block[worn]`,
   `test_nose_never_touches_filament`.
4. **Tubes routing out.** The inlet tube goes straight up between the three markers, and the outlet tube drops past
   the clip's front wall. `test_tube_paths_clear`.
5. **The outlet socket on the bed face.** Elephant foot would close the mouth, so it gets a chamfer.
   `test_outlet_mouth_chamfered`.

---

### Task 1: `cadkit.checks.overhangs`

**Files:**
- Modify: `cadkit/cadkit/checks.py` (add after `downward_faces`)
- Test: `cadkit/tests/test_checks.py`

**Interfaces:**
- Produces: `overhangs(part: Shape, max_deg: float = 45.0) -> list[tuple[float, float]]`. It returns (z, area) for
  every face that has triangles facing down more steeply than `max_deg` from vertical, above the bed. Rule: a
  triangle counts when `-n.Z > sin(radians(max_deg)) + 1e-3` and its lowest vertex is above z = 1e-6. Tessellate
  each face (0.05, 0.2), as `open_edges` does.

- [ ] **Step 1: Write the failing tests**

```python
def test_overhangs_flag_shallow_undersides_only():
    upright = Cylinder(5, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    assert overhangs(upright) == []
    lean = lambda deg: Pos(0, 0, 10) * Rot(0, deg, 0) * Cylinder(5, 30)   # axis `deg` from vertical, above the bed
    assert overhangs(lean(30)) == []          # underside 30° from vertical
    assert overhangs(lean(60)) != []          # underside 60° from vertical
    roof = Pos(0, 0, 5) * Cone(10, 0, 10)     # a 45° roof prints
    assert overhangs(roof) == []
```

- [ ] **Step 2:** `cd cadkit && uv run pytest tests/test_checks.py -k overhangs`. It should FAIL with an ImportError.
- [ ] **Step 3:** Implement `overhangs` with the signature and rule above. Its docstring says it's for angled
  undersides and that `downward_faces` covers flat ones.
- [ ] **Step 4:** Run it again; it should PASS. Then run `uv run pytest -n 4` and expect it all green.
- [ ] **Step 5:** Commit: "cadkit: overhangs check for undersides steeper than 45°".

### Task 2: Project scaffold, params and layout math

**Files:**
- Create (via `cadkit.new`): `examples/sharpie-colorizer/` with package `sharpie_colorizer`. `docs/` already
  exists: move it to the scratchpad, run `uv run --project cadkit python -m cadkit.new sharpie-colorizer`, then
  move `docs/specs`, `docs/plans` and `docs/measurements.md` back. Delete the template's `parts.py`/`build.py`
  coupon code as each task replaces it, and the coupon test now.
- Replace: `sharpie_colorizer/params.py`
- Create: `sharpie_colorizer/layout.py`, `tests/test_layout.py`

**Interfaces:**
- Produces `Params` (frozen dataclass) and `P`, with these fields and defaults:
  - **Measured:** `bar_w=40, bar_h=20, bar_r=3.0` (bar_r is assumed; it's only used to model the bar),
    `marker_body_d=13.0, marker_front_d=11.0, front_straight_l=20.0, shoulder_to_felt_long=32.0,
    shoulder_to_felt_short=28.5, nose_l=6.0, nose_d=6.0` (nose_d is assumed), `felt_l=5.0, felt_d=4.0,
    filament_d=1.75, tube_od=4.0`.
  - **Fits** (the fit test picks these): `marker_fit_d=11.0, marker_fits=(10.6, 10.8, 11.0, 11.2, 11.4, 11.6),
    tube_fit_d=4.1, tube_fits=(4.0, 4.1, 4.2, 4.3), hook=2.0, hooks=(1.5, 2.0, 2.5)`, `clip_clear=0.2` (per side
    around the bar), `rail_clear=0.1` (per side: the railroad's proven 0.2 mm slide).
  - **Design:** `tilt_deg=42.0, azimuths_deg=(270.0, 30.0, 150.0), stagger=8.0, felt_press=0.3, grip_min=12.0,
    shoulder_gap_min=3.0, wear_max=1.0, channel_d=2.4, wall=2.4, nose_clear=1.0, felt_clear=0.3, tube_depth=10.0, bed_chamfer=0.4,
    clip_w=20.0, clip_t=2.4, rail_neck=8.0, rail_head=11.0, rail_h=4.0, floor_t=1.2, tip_lift=3.0, inlet_gap=3.0,
    filament_black=3, printer=Printer()`.
  - `__post_init__` snaps `rail_h`, `floor_t` and `tube_depth` to layers, like the candle project does.
- `layout.py` (pure math, no CAD), each function taking `p: Params = P`:
  - `tip_r(p) -> float` = filament_d/2 − felt_press (0.575)
  - `axis(p, i) -> tuple[float, float, float]`: unit vector from the felt point up and out:
    (sin t·cos φᵢ, sin t·sin φᵢ, cos t)
  - `straight_from_tip(p, reading: str) -> float` = felt_l + (shoulder_to_felt_[reading] − front_straight_l),
    where reading is "long" or "short"
  - `shoulder_from_tip(p, reading) -> float` = felt_l + shoulder_to_felt_[reading]
  - `mouth_l(p) -> float` = straight_from_tip(p, "long") + grip_min (29.0)
  - `fit_start_l(p) -> float` = felt_l + nose_l (11.0): where the Ø fit bore starts
  - `nose_start_l(p) -> float` = felt_l − wear_max − 0.5 (3.5): where the nose bore starts, low enough for a worn
    marker's nose
  - `channel_y(p) -> float` = bar_w/2 + clip_clear + clip_t + tube_od/2 + 1.0 (25.6)
  - `cone_h(p) -> float` = (tube_fit_d − channel_d)/2 (a 45° step from the tube socket to the channel)
  - `base_t(p) -> float` = layer-snapped (rail_h + rail_clear + rail_head/2 + rail_clear + floor_t). That's the
    rail slot with a 45° peaked roof, plus a floor.
  - `tip_point(p, i) -> tuple[float, float, float]` in the block frame: (tip_r·cos φᵢ, channel_y + tip_r·sin φᵢ,
    base_t + tip_lift + i·stagger)
  - `top_z(p) -> float` = snap(tip z of the last marker + felt_l·cos t + inlet_gap + cone_h + tube_depth)
  - `boss_r(p) -> float` = marker_fit_d/2 + wall
  - `nose_reach(p) -> float` = tip_r + nose_start_l·sin t − (nose_d/2 + nose_clear)·cos t. This is the signed
    distance of the nose bore's innermost edge from the channel axis, measured toward its own side. It may nick
    its own side of the channel, but it must leave the far half alone: `nose_reach > −channel_d/2 + 0.4`. That
    way the opposite wall still guides.
  - `clip_strain(p, hook) -> float` = 3·clip_t·hook / (2·(bar_h + 2·clip_clear + clip_t)²)
  - `validate(p) -> None`: raises ValueError naming the value and the fix in three cases:
    - shoulder_from_tip(short) − mouth_l − wear_max < shoulder_gap_min
    - nose_reach ≤ −channel_d/2 + 0.4 ("raise tilt_deg or measure nose_d")
    - clip_strain(max(hooks)) > 0.02

- [ ] **Step 1: Write the failing tests** (`tests/test_layout.py`)

```python
def test_grip_and_wear_from_the_measurements():
    assert mouth_l(P) - straight_from_tip(P, "long") == pytest.approx(P.grip_min)
    assert shoulder_from_tip(P, "short") - mouth_l(P) - P.wear_max >= P.shoulder_gap_min
    assert mouth_l(P) - straight_from_tip(P, "short") >= P.grip_min   # more grip at the short reading

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
        assert z == pytest.approx(base_t(P) + P.tip_lift + i * P.stagger)

def test_clip_flex_stays_elastic_for_every_hook():
    assert all(clip_strain(P, h) <= 0.02 for h in P.hooks)

def test_heights_on_layers():
    assert P.printer.on_layer(base_t(P)) and P.printer.on_layer(top_z(P))
```

- [ ] **Step 2:** `cd examples/sharpie-colorizer && uv sync && uv run pytest tests/test_layout.py`. It should FAIL
  on imports.
- [ ] **Step 3:** Write `params.py` and `layout.py` per the Interfaces above.
- [ ] **Step 4:** Run it again; it should PASS.
- [ ] **Step 5:** Commit: "Sharpie colorizer: project, params from the measurements, layout math".

### Task 3: Shared cutters and profiles (`joints.py`)

**Files:**
- Create: `sharpie_colorizer/joints.py`, `tests/test_joints.py`

**Interfaces** (all in a local frame; callers place them):
- `marker_cavity(p, fit_d: float | None = None) -> Part`: along +Z, with the felt point at the origin. It's the
  union of three pieces:
  - the felt cone: radius 0 at z = −felt_clear, out to felt_d/2 + felt_clear at z = felt_l;
  - the nose bore: Ø nose_d + 2·nose_clear, from z = nose_start_l to fit_start_l + 0.5;
  - the fit bore: Ø fit_d (default p.marker_fit_d), from fit_start_l to mouth_l + 5.
  Overlap each pair by 0.5 so they union cleanly.
- `marker_solid(p, reading: str, wear: float = 0.0, with_grip: bool = False, felt: bool = True) -> Part`: the
  Sharpie, felt point toward −Z. It's built from felt cone, nose, round-in (Ø11 → nose_d over the length that's
  left), the Ø11 straight section, and the Ø13 body (100 mm). A worn marker has its felt cone cut off `wear` short
  and sits `wear` deeper, so its blunt felt end touches at z = 0 and everything behind is `wear` lower.
  `with_grip=False` leaves the gripped Ø11 straight section out, so the clash tests see only the parts that must
  not touch plastic. `felt=False` leaves the felt out, for the nose-vs-filament check.
- `tube_socket(p, fit_d: float | None = None) -> Part`: along +Z from a mouth at z = 0. A cylinder Ø fit_d,
  tube_depth deep, then a 45° cone down to channel_d, length cone_h.
- `rail_profile(p, clearance: float = 0.0, peaked: bool = False) -> Sketch`: in the (Y, Z) plane as (u, v). A
  trapezoid with its neck rail_neck at v = 0, widening to rail_head at v = rail_h, grown by `clearance`. `peaked`
  adds a 45° roof above the head, which is how the block cuts the slot.
- `clip_profile(p, hook: float) -> Sketch`: in (u = Y, v = Z) with the bar centered on the origin. A C around a
  rounded rectangle bar_w × bar_h grown by clip_clear, with walls clip_t thick. The top web's top is at
  v = bar_h/2 + clip_clear + clip_t. The two bottom lips reach `hook` inward under the bar's bottom edge, with a
  45° lead-in on their lower inside faces. The rail sits on top, centered on u = 0. The opening at the bottom is
  bar_w − 2·hook wide.

- [ ] **Step 1: Write the failing tests**

```python
def test_marker_fits_its_cavity_at_both_readings():
    for reading in ("long", "short"):
        for wear in (0.0, P.wear_max):
            below_mouth = marker_solid(P, reading, wear) & Box(60, 60, mouth_l(P), align=(Align.CENTER, Align.CENTER, Align.MAX)).moved(Location((0, 0, mouth_l(P))))
            assert (below_mouth - marker_cavity(P)).volume == pytest.approx(0, abs=1e-3)   # only the grip touches

def test_cavity_fit_bore_diameter_and_reach():
    cav = marker_cavity(P)
    probe = lambda r, z0, z1: Pos(0, 0, z0) * Cylinder(r, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    lo, hi = straight_from_tip(P, "long"), mouth_l(P)
    assert (probe(P.marker_fit_d / 2 - 0.01, lo, hi) - cav).volume == pytest.approx(0, abs=1e-3)
    assert (probe(P.marker_fit_d / 2 + 0.1, lo, hi) - cav).volume > 0

def test_tube_socket_depth_and_cone():
    s = tube_socket(P)
    assert s.bounding_box().max.Z == pytest.approx(P.tube_depth + cone_h(P))

def test_clip_profile_lips_leave_the_hook_opening():
    bb = clip_profile(P, P.hook).bounding_box()
    assert bb.max.Y == pytest.approx(P.bar_w / 2 + P.clip_clear + P.clip_t)   # bounding box in (u, v)
```

- [ ] **Step 2:** Run `uv run pytest tests/test_joints.py`. It should FAIL.
- [ ] **Step 3:** Implement the five functions per the Interfaces above.
- [ ] **Step 4:** Run it again; it should PASS.
- [ ] **Step 5:** Commit: "Sharpie colorizer: marker cavity, marker model, tube socket, rail and clip profiles".

### Task 4: Fit-test plate (prints first)

**Files:**
- Create: `sharpie_colorizer/parts/fittest.py`, `tests/test_fittest.py`
- Create: `sharpie_colorizer/build.py`, which starts with just the `fit` command: STEP + plate + `render/fit_test.png`

**Interfaces:**
- `marker_strip(p) -> Part`: a 15 mm tall block. Each bore is a `marker_cavity` fit bore of `marker_fits[k]`, at
  `tilt_deg` from vertical, tilted along X, opening on the top face and running out through the bottom face. Every
  diameter gets a 1.2 mm wall at its narrowest. Each bore k gets k + 1 raised bars (fit-coupon style: 1.2 × 4 ×
  0.6 mm) on the top face beside it.
- `tube_strip(p) -> Part`: 10 mm tall, with a straight through-hole for each `tube_fits[k]`, a `bed_chamfer` on
  the bed mouth, and k + 1 bars.
- `clip_slice(p, k: int) -> Part`: `clip_profile(p, hooks[k])` extruded 8 mm, lying with the profile on the bed,
  with k + 1 bars on its top face.
- `fit_items(p) -> list[tuple[str, Part]]`: `marker_strip`, `tube_strip`, and `clip_slice_{k}` for each hook.

- [ ] **Step 1: Write the failing tests**: each of these for every item in `fit_items(P)`:
  `printable_problems == []`, `open_edges == 0`, `off_layer_z == []`, `downward_faces == []`, and
  `overhangs == []`. Also:

```python
@pytest.mark.parametrize("k", range(len(P.marker_fits)))
def test_marker_strip_bore_k_is_its_size(k):  # probe along bore k's axis: Ø−0.01 clear, Ø+0.1 hits plastic
    ...
@pytest.mark.parametrize("k", range(len(P.tube_fits)))
def test_tube_strip_hole_k_is_its_size(k): ...
def test_clip_slice_holds_the_bar(k):  # bar (rounded rect, bar_r) ∩ slice == 0; same bar raised 1 mm ∩ slice > 0
    ...
def test_every_variant_is_numbered(): ...  # bar count per variant == k + 1, by probing the top face
```

- [ ] **Step 2:** Run `uv run pytest tests/test_fittest.py -n 4`. It should FAIL.
- [ ] **Step 3:** Implement `fittest.py`. In `build.py`, `main(["fit", "--out", d])` packs `fit_items` onto plate
  `fit_test_1` in black (`filament_black`), exports STEP per item, and renders `render/fit_test.png`.
- [ ] **Step 4:** Run it again; it should PASS. Then run `uv run python -m sharpie_colorizer.build fit` and look at
  `out/render/fit_test.png`.
- [ ] **Step 5:** Slicer check: `slicers.active().slice_report` on `out/plates/fit_test_1.3mf` slices in black
  only. Add it as a `@pytest.mark.slow` test, copying the candle project's.
- [ ] **Step 6:** Commit: "Sharpie colorizer: fit-test plate". **Send `out/plates/fit_test_1.3mf` and the render to
  the user to print now.** The later tasks don't wait. Their picks become one-line `params.py` edits.

### Task 5: Clip

**Files:**
- Create: `sharpie_colorizer/parts/clip.py`, `tests/test_clip.py`

**Interfaces:**
- `make(p) -> Part`: `clip_profile(p, p.hook)` extruded `clip_w`, with the profile on the bed. Print orientation
  is the profile in XY, so the snap flexes along the layers. Shift it into the first quadrant and give it the label
  `"clip"`.
- `place(p) -> Location`: puts the extrusion axis along use X, centered at X = 0, with the profile in use (Y, Z) as
  drawn.

- [ ] **Step 1: Write the failing tests:** printable, watertight, on layers, `downward_faces == []`,
  `overhangs == []`. Also:
  - `test_clip_holds_the_bar`: bar ∩ placed clip ≈ 0, and the clip raised 1 mm in Z ∩ bar > 0.
  - `test_nothing_below_the_lips`: the placed clip's `min.Z ≥ −bar_h/2 − clip_clear − clip_t − 1e-3`.
  - `test_rail_on_top_at_center`: the rail's top is at `bar_h/2 + clip_clear + clip_t + rail_h`, and its head
    width at that height is `rail_head` (thin-probe measurement).
- [ ] **Step 2:** Run it; it should FAIL.
- [ ] **Step 3:** Implement it.
- [ ] **Step 4:** Run it; it should PASS.
- [ ] **Step 5:** Commit: "Sharpie colorizer: snap clip with the dovetail rail".

### Task 6: Marker block

**Files:**
- Create: `sharpie_colorizer/parts/block.py`, `tests/test_block.py`

**Interfaces:**
- `body(p) -> Part` (block frame, before cuts), the union of:
  - the base: box X ±clip_w/2, Y from −(rail_head/2 + rail_clear + wall) to channel_y + boss_r, Z 0..base_t;
  - the column: a cylinder of radius tube_fit_d/2 + wall at (0, channel_y), Z 0..top_z;
  - per marker, a boss: a cylinder of radius boss_r along axis(i) from tip_point(i), running from L = −boss_r to
    mouth_l, with its end face perpendicular to the axis.
  All of it is intersected with Z ≥ 0.
- `make_use(p) -> Part` (block frame) = body minus these cuts:
  - the channel Ø channel_d, full height;
  - a `tube_socket` from the bottom mouth up, plus a `bed_chamfer` at z = 0;
  - a `tube_socket` flipped down from the top;
  - for each marker i, `marker_cavity` placed with its local +Z along axis(i) and its origin at tip_point(i);
  - the rail slot: `rail_profile(p, rail_clear, peaked=True)` extruded through X, at Y = 0 from Z = 0.
- `make(p) -> Part` = make_use shifted into the first quadrant (print orientation = use orientation, base on the
  bed), labeled `"block"`.
- `place(p) -> Location`: block frame → use frame. Z lifts by bar_h/2 + clip_clear + clip_t + rail_clear, so it
  sits on the rail with clearance. Note: the slot floor clears the clip web by rail_clear.

- [ ] **Step 1: Write the failing tests:**
  - printable, watertight, on layers, `downward_faces == []`, `overhangs == []`
  - `test_channel_clear_full_height`: a Ø filament_d rod on the channel axis from z = 0 to top_z ∩ block == 0.
  - `test_opposite_wall_guides_past_every_window` (Review Focus 1): at each tip_point(i) height, a 0.2 mm probe
    box just outside the channel wall (r = channel_d/2 + 0.1) on azimuth φᵢ + 180° ∩ block > 0.
  - `test_marker_socket_grips_the_straight_section` (per i): the same two probes as the joints test, along
    axis(i) in the block frame.
  - `test_nothing_past_the_mouth` (per i): a Ø(marker_body_d + 1) ring from mouth_l + 0.5 to mouth_l + 40 along
    axis(i) ∩ block == 0, so the body never seats.
  - `test_tube_sockets` (inlet and outlet): Ø tube_fit_d − 0.01 for tube_depth ∩ block == 0; Ø tube_fit_d + 0.3
    > 0.
  - `test_outlet_mouth_chamfered` (Review Focus 5): the hole's width at z = 0.1 is ≥ tube_fit_d + bed_chamfer.
  - `test_slot_takes_the_rail`: the rail profile extruded at the slot ∩ block == 0, and the rail grown by
    rail_clear + 0.1 ∩ block > 0.
- [ ] **Step 2:** Run `uv run pytest tests/test_block.py -n 4`. It should FAIL.
- [ ] **Step 3:** Implement it. Render `out/render/section.png`, cut through the channel axis on the plane of
  marker 0, and **look**: windows, opposite wall, bores.
- [ ] **Step 4:** Run it; it should PASS.
- [ ] **Step 5:** Commit: "Sharpie colorizer: marker block with staggered windows on a guided channel".

### Task 7: Assembly, clashes and keep-outs

**Files:**
- Create: `sharpie_colorizer/assembly.py`, `tests/test_assembly.py`

**Interfaces:**
- `bar(p, length=120.0) -> Part`: the frame bar in the use frame, a rounded rectangle bar_w × bar_h, radius bar_r,
  along X.
- `marker(p, i, reading="long", wear=0.0, felt=True) -> Part`: `marker_solid(p, reading, wear, felt=felt)` placed
  with local +Z along axis(i) and its origin at tip_point(i) (block placement applied).
- `filament(p) -> Part`: a Ø filament_d rod on the channel axis, through the block's full height.
- `tube_paths(p) -> list[tuple[str, Part]]`: the inlet is a Ø tube_od cylinder from the inlet socket floor
  straight up 60 mm. The outlet runs from the outlet socket floor straight down to Z = −bar_h/2 − 20.
- `placed_parts(p, reading="long", wear=0.0) -> list[tuple[str, Part]]`: the bar, clip, block, marker_0..2 and
  the tube paths. The filament is not included, because felt is meant to touch it.

- [ ] **Step 1: Write the failing tests:**

```python
@pytest.mark.parametrize("reading,wear", [("long", 0), ("short", 0), ("short", P.wear_max)], ids=["long", "short", "worn"])
def test_markers_clear_block(reading, wear):          # Review Focus 2 & 3
    assert find_clashes(placed_parts(P, reading, wear)) == []

def test_clash_test_can_fail():                        # worn far past wear_max, the nose hits plastic
    assert find_clashes(placed_parts(P, "short", P.wear_max + 3.0)) != []

def test_nose_never_touches_filament():                # Review Focus 3: everything but the felt stays off it
    for i in range(3):
        assert (marker(P, i, "short", P.wear_max, felt=False) & filament(P)).volume == pytest.approx(0, abs=1e-3)

def test_felt_reaches_the_filament():                  # each felt overlaps a Ø filament_d rod on the channel axis
    ...

def test_tube_paths_clear():                           # Review Focus 4: included in placed_parts; asserts by name
    ...

def test_gantry_space_empty():                         # every placed solid except the bar and the outlet tube
    ...                                                # has min.Z ≥ −bar_h/2 − clip_clear − clip_t − 1e-3
```

- [ ] **Step 2:** Run it; it should FAIL. **Step 3:** Implement it. **Step 4:** Run it; it should PASS. If a marker
  clashes with another boss, raise `stagger` or rotate `azimuths_deg` in params, not in the code.
- [ ] **Step 5:** Commit: "Sharpie colorizer: assembly on the bar with markers and tube paths, clash-free".

### Task 8: Plates, build, renders, README, docs

**Files:**
- Modify: `sharpie_colorizer/build.py` (the default `all` builds `fit` plus parts: STEP clip/block/assembly, plate
  `colorizer_1` with clip + block in black, renders `assembly.png` (iso, bar stub, markers in red, tubes in white)
  and `section.png`)
- Create: `sharpie_colorizer/plates.py` (`plates(p) -> list[Plate]`: `fit_test_1`, `colorizer_1`),
  `tests/test_build.py`
- Modify: `README.md` (opens with `docs/images/assembly.png`, `section.png` and `fit_test.png`, then what to print,
  how to fit it, and loading/unloading: pull the markers back a few mm before unloading)
- Modify: the root `CLAUDE.md` (one line under the examples), and the spec's Amendments (below)

- [ ] **Step 1: Write the failing tests:** `build.main(["--out", tmp])` writes `step/clip.step`,
  `step/block.step`, both plates and the three renders. Each plate opens in black only (`read_filaments`, like the
  candle test). A slow test runs both plates through `slicers.active()`: `roundtrip` + `same_objects`, and
  `slice_report` layers all black.
- [ ] **Step 2:** Run it; it should FAIL. **Step 3:** Implement it. **Step 4:** Run it; it should PASS, then run
  the slow tests in the background: `uv run pytest -n 4`.
- [ ] **Step 5:** Copy `out/render/*.png` to `docs/images/` and **look at each one**. Then run
  `cd ../../cadkit && uv run pytest tests/test_examples.py`; it should PASS.
- [ ] **Step 6:** Add a spec amendment (2026-10-18, builder's choices):
  - The package is `sharpie_colorizer` (what `cadkit.new` makes).
  - Two parts: a clip printed on its profile, and a block printed upright, joined by a dovetail rail with a peaked
    slot roof.
  - Tilt is 42°, the top end of the range, so the nose bore clears the channel.
  - Windows are staggered 8 mm along a continuous Ø2.4 channel, so a loading end is guided past each felt.
  - Mouth at 29 mm from the felt point (12 mm of grip). Felt wear allowance is 1 mm.
  - The nose bore may nick its own side of the channel, but never the far half.
  - Clip hook fit-tested at 1.5/2.0/2.5 mm.
- [ ] **Step 7:** Commit: "Sharpie colorizer: plates, build, renders and README".

### Task 9: Independent review before printing

- [ ] **Step 1:** Dispatch a fresh reviewer, per the root CLAUDE.md, on `parts/` and `assembly.py`. It checks:
  print orientation, `downward_faces`/`overhangs`, thin walls (minimum wall between each cavity and the outside,
  and between cavities), the snap's strain, the rail fit, and assembly order (clip onto the bar, block onto the
  rail, tubes in, markers in). It proves each finding with a probe.
- [ ] **Step 2:** Fix the real findings test-first. Then run the fast suite: `uv run pytest -n 4 -m "not slow"`
  should be all green.
- [ ] **Step 3:** Commit, then send the user `colorizer_1` and the renders.
