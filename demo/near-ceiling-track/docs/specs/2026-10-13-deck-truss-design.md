# Straight runs: deck truss option — design spec (2026-10-13)

Reference: Atlas-style deck truss (track on top, zig-zag Warren web with thin uprights, X sway bracing
between the two trusses). Chosen end treatment: **A, truss between piers**.

## Goal
An alternative look for the straight-run viaduct that keeps the snap-together kit and every interface
it has with the wall brackets, tie ladders and bus wiring. The arch viaduct stays the default.

## Switch and snapshot
- `run_style: str = "arch"` in `params.py`, with `"deck_truss"` as the alternative. The default flips only after the user approves.
- Tag `arch-viaduct-v1` marks the last commit before this work. Development happens on branch `feat/deck-truss`.

## What changes
- **Panel profile** (`arch_half.profile`, dispatched on `run_style`). It is still a flat-printed half panel,
  4 per bay, joined at mid-bay by the same bow-tie keystone. In (u, z), with u from the pier centerline and
  z = 0 at the tie underside:
  - **Half pier** `rect(0, pier_w/2, -pier_depth, 0)`: unchanged, with the same bracket tongue notch and latch window.
  - **Top chord** = today's top band `rect(0, h, -top_band_h, 0)` plus the same tabs into the tie ladder.
  - **Inclined end post** from the pier face just below the top chord down to the bottom chord at the
    first post (u = 2"). Width `dt_post_w`.
  - **Bottom chord** `rect(first post − lap, h, -pier_depth, -pier_depth + dt_chord_h)`, so it is
    flush with the pier bottom (the truss depth equals `pier_depth` = 3").
  - **Warren web**: diagonals zig-zag between bottom panel points (the posts, every 2", and mid-bay) and top
    points halfway between them. Thin uprights sit at each post.
  - **Mid-bay block**: a full-depth upright `crown_block_w` wide, holding the keystone socket at mid-depth.
  - Members overlap by at least 1 mm, and gussets sit at the chord joints. Edge-to-edge joints make invalid 3MF meshes.
- **`layout.rib_low`** (the lowest material at u) becomes style-aware. It follows the end post's
  underside up to the first post, then sits at `-pier_depth`. `cf_depth` and the cross-frame notches follow
  automatically.
- **Cross-frames** get an X sway brace in the open middle between the two trusses (style-aware cut).
  The slots, bar, bus finger and lip are unchanged.

## What doesn't change
The wall bracket, snap latch, pier tongue, tie ladders, handrail, end piers, run ends,
plates and packing, and the bus cradle.

## Tests (each written before its code)
- Panel printable and 3MF-valid for every bay length in `BAYS` and for min/max bay.
- Bottom chord underside at `-pier_depth` past the first post; top chord continuous.
- Web count at mid-depth: 1 end post + the Warren diagonals + the uprights, derived from `post_us`.
- `rib_low` matches the end-post slope and the bottom chord; cross-frame notch depth ≥ `rib_notch`.
- The existing assembly clash test, bracket-latch engagement test and plate packing stay green for both styles.
- `run_style="arch"` output is unchanged (STEP of an arch half matches the tag's volume).

## Amendments (2026-10-13, after the side-by-side review)

- **Truss depth 2.25"** (`dt_depth`, about 16 scale ft, roughly 1/7 of a 16" span). This replaces "depth = pier_depth".
  The pier stays 3" deep and runs about ¾" below the bottom chord, like a real pier. Bracket, tongue and latch are unchanged.
- **Concrete-look pier**: a ledge under the top chord (`pier_cap_h` 4, `pier_cap_out` 1.5) and sides that
  flare out toward the bottom (`pier_batter` 2.5 mm). Only the outer outline changes.
- **Mid-bay joint**: a small bow-tie (`dt_key_*` 8 × 8, waist 4.5) sits in a bottom-chord splice plate
  (`dt_gusset_w` 7 × `dt_gusset_h` 12 per half), so the mid-bay post is slim (`dt_mid_w` 2.5 per half). The key sits where
  the bottom chord pulls apart, which a friction U-clip would handle poorly. `keystone.key_params/key_z` pick the
  key per style. The fit-test coupon samples whichever key the style uses.
- **Cross-frames**: stacked X sway bracing in the window (`x_cells`, cells about 2:1). Arch keeps the open window.
- **Warren web**: apexes alternate bottom/top at each 2" post (diagonals about 55°), uprights at every post after the foot.
- **CLI**: `--run-style deck_truss` and `--corner-style bowstring` on any build command (additive).
- **Handrail**: deck truss runs get a short single-bar walkway railing, 12 mm above the rail (`dt_handrail_h`, ~3.5 scale ft). It is still
  the derail catch. `checks.tip_catch_angle` tips a 60 ft car body (sill `car_sill_h` 12, height `car_body_h` 41) toward the room about
  the rail head and finds the lean at first contact. The short railing catches at 17.5° and the arch's 19 mm railing at 12°. The test
  requires ≤ 25°, and a 1.5 mm railing fails it.
- **Deferred**: a pier face plate to close the two-slab gap seen end-on, and deck plate girders for bays under ~11".
- **Solder gap (every straight-run bay, both styles).**
  - `solder_gap`: the plain ties between the two handrail-post ties nearest each bay's mid (3 ties, ~20 mm) form the gap.
  - Feeders solder to the **outside** of the rail. The gauge side stays clear for deep vintage flanges.
  - Over the gap each runner is notched from the rail groove's outer edge outward, so the iron and feeder reach the rail base.
  - The runners' inner parts stay continuous and carry the rail. The gap ties keep their center part between the rails.
  - On the room side they keep a 2.8 mm end stub (`solder_room_stub`), held by a 1 mm bar on top (flush with the tie tops, set 0.8 mm
    back) that runs post to post, hidden from below, so the tie line reads unbroken from the room. Corners get no feeders.
- **Two-color tie ladders.** Brown ties, runners and tabs, then gray tie plates, shoulders and lips on the top layers:
  one color change. Painted as one part in CAD (`tie_ladder.painted`). Plates use `make_colored`.
- **Bracket half-lap (both styles).** `pier_notch` is now half the pier depth (1.5"). The panels' pier notch goes up half
  the pier, and the bracket's pier slots come down only the other half, so the bracket keeps a solid ~42 mm lower block
  instead of 5 mm. Install order is unchanged: brackets on the wall, then the trusses drop in, then the deck, handrail
  and track.
- **Print-readiness review (2026-10-13).** An independent reviewer found these; all fixed except the last:
  - Two-color parts are written as ONE 3MF object with two parts (`build.add_multipart`). Separate objects would be
    dropped onto the bed by the slicer.
  - `tie_h` 2.3 → **2.4**, so the color seam and every top land on 0.2 mm layers.
  - `screw_d` 3.6 → **4.6** (#8 screws into studs or drywall anchors).
  - Cross-frames can only go in from below, so a bay's panels and cross-frames are glued into a box on the bench and
    dropped into the brackets (README install order).
  - The room rail's feeder has a passage under the rail through the runner (`solder_feed_w`), so it drops hidden
    between the panels.
  - The deck truss bottom chord starts before the first post, giving the first cross-frame notch walls on both sides.
  - Handrail sockets use `fit_slide` plus glue.
  - End piers get the concrete-look outline on deck truss runs.
  - Not fixed: a 0.98 mm wall in the corner rod anchor between the latch relief and the rod bore. It prints with two perimeters.
- **Plates.** Two-color parts never share a plate with single-color parts, so each plate has at most one color change
  (AMS lite swaps are slow). `plates.all_in_one` packs a short run (the starter bay) onto the fewest plates.
