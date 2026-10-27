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

## Amendments (2026-10-14): feeder groove under both rails

- **The room rail's feeder now goes all the way to the wall side**, where the bus is. A groove runs straight across
  under **both** rails (it was a passage under the room rail only, dropping between the panels).
- **It sits in the gap's first opening**, between the full tie at the gap's low-x end and the first gap tie (it was
  one opening further in). The wire comes up at the end of the gap, and the rest of the gap is free to bend it along
  the rail and solder.
- **The groove has a floor** (`solder_feed_floor` 0.8 mm, 1.6 mm deep, `solder_feed_w` 1.6 wide). With full-depth
  cuts in both runners, the only thing joining the ladder across the groove would be the 1 mm bar over the room-side
  stubs. The floor keeps each runner, and so the ladder, in one piece.
- Tests: the groove is clear from the wall-side tie ends to the room-side stubs, with its floor intact, for bays
  from 8" to the 480 mm max. In the run assembly a 22 AWG wire in the groove touches no part, for both run styles.

## Amendments (2026-10-14): plates open colored; no tie plate over a tab slot

- **Bambu Studio project 3MF.** The user's first look in Bambu Studio showed "the 3mf is not from Bambu Lab, load
  geometry data and color data only", with every part on filament 1. Bambu Studio only reads a filament per part from
  its own project format.
  - `hotrain/bambu3mf.py` now writes every plate that way. Each printed part is one object, each color body one part,
    and `Metadata/model_settings.config` gives each part a filament: `filament_gray` 1, `filament_brown` 2,
    `filament_white` 3 (the user's AMS).
  - `Metadata/project_settings.config` comes from `hotrain/bambu_project_settings.config`, saved by Bambu Studio
    2.08 (A1 0.4, 0.20mm Standard, PETG Basic, filament 3 recolored white). Without it the Bambu CLI crashes on
    the project.
  - Checked against Bambu Studio itself: it re-saves the plate with the same filament per part, and slicing a ladder
    plate prints layers 0–11 brown and 12–18 gray, one change.
  - **Mesh ids are unique across the whole file.** Bambu Studio keys meshes by object id alone, whatever file
    they're in. The first version numbered each object file from 1, so the starter plate's three ladders all opened
    as copies of the middle one, gaps included. Ids now run in one sequence (meshes, then their object), as Bambu
    writes them. The round-trip test checks that every object keeps its own geometry.
- **No tie plate over a tab slot.** A tie sits centered on every panel tab, so its tie plate bridged the 3.4 mm slot
  (it would need supports). That tie now gets no plate and the slot runs up through it, open to the sky. Steel is
  also clipped to the wood's footprint, which trims the 0.5 mm the first plate hung over each jigsaw socket.

## Amendments (2026-10-14): generic tooling moves to cadkit

- The repo became **claude-cad**, a general CAD tool with this railroad as its big example. Code that any project
  needs moved out of `hotrain` into `cadkit/` (repo root), and `hotrain` imports it: `paint`, the plate packer
  (`cadkit.plates`), the Bambu writer and its settings template (`cadkit.bambu3mf`,
  `cadkit/cadkit/bambu_a1_project_settings.config`), print checks (`cadkit.checks`), the clash finder
  (`cadkit.clash`), plate and SVG export (`cadkit.export`) and the viewer helper (`cadkit.view`).
- Project-specific code stays: `hotrain.build.filament` (brown wood, white cleats, gray otherwise), the kits, the
  derail-catch check. `Params.printer` hands the bed size to cadkit. The viewer's network setting is now
  `CADKIT_VIEWER_HOST` (was `HOTRAIN_VIEWER_HOST`).
- No geometry changed; the full suite passes as before.

## Amendments (2026-10-14): real Code 100 rail profile

- The rail is **Walthers 948-10000** (Code 100 nickel silver, 36", pkg 17). Walthers doesn't publish its profile, so
  params now use the NMRA RP-15.1 Code 100 nominals instead of guesses: base 0.090" (2.286 mm, was 2.2), head
  0.045" (1.143 mm, was 1.1), base edge 0.018" (0.457 mm) with its top rising 15°, head depth 0.023". Measure the
  real rail with calipers when it arrives and update these.
- Effect: groove 2.486 mm (0.1 mm play per side); rail centers 17.743 mm apart (was 17.7).
- **The lip check is now a test.** With the base's real edge and slope, the base slides under the 0.6 mm-high lip
  with 0.089 mm to spare (room for a slightly drooping printed overhang), and the 0.3 mm lip still overlaps the base
  by 0.1 mm with the rail pushed hard against the gauge-side shoulder. One side only stays: a lip on the gauge side
  would sit 1.54 mm below the railhead, inside the 1.6 mm deep-flange limit.
- The fit coupon's three groove samples now give 0.05 / 0.1 / 0.15 mm play per side against the real base. If the
  rail won't go under the lips on any of them, raise `shoulder_h` to 0.8.
- **2026-10-16, the bed comes from settings.** `bed`, `bed_y` and `bed_margin` in params now default to the user's
  `cadkit.settings` (`CADKIT_BED...` or `cadkit.toml`) instead of a hard-coded 256 mm; with nothing set they are
  still the A1's 256 × 256 and 5 mm, so every plate is unchanged. `bed_usable` is the shorter side. Half spans and
  ladders are still sized for the A1: on a smaller bed the fit tests fail with the numbers. Slicer tests go
  through `cadkit.slicers.active()` and skip when no slicer is installed.

## Amendments (2026-10-17): rivet heads

- **Rivet heads on the room face**, gray bumps for realism: 0.8 mm across, 0.4 mm (two layers) proud, at 2.5 mm
  along each member.
  - Two rows along each chord and the end post, one along each vertical, diagonal and the mid-bay post, and a grid
    on the splice plate. The concrete-look pier stays bare.
  - A head is kept only where the whole dot (plus 0.2 mm) stands on the member, and never touches another head.
  - None within the cross-frames' slots at each post: they grip both panels there, and the assembly clash test
    caught heads inside them. The verticals sit behind the cross-frames, so they carry none.
  - Real HO heads are about 0.3 mm, too small for the 0.4 mm nozzle; 0.8 mm is the smallest that prints round.
    Bambu prints them: the slow test slices a pair of halves up to the rivet tops.
- **Each panel prints a mirror-image start half.** The halves print rivets-up. The start half used to be the end
  half turned 180°, which would have put its rivets on the wall side.
  - Each bay is now 2 end halves + 2 start halves (`arch_half_<bay>` and `arch_half_<bay>_start`). Each half-span
    plate prints one of each, named on the plate so you can tell them apart in Bambu Studio and in `plates.csv`.
  - A mirror pair can't nest head-to-tail (that needs one half flipped over, rivets down), so the pair is 17 mm
    deeper. On the room's 418.2 mm bays a cross-frame no longer fits its plate. A kit's overflow now goes to
    shared `extras` plates, like the pooled ladders.
  - The room comes out at 19 distinct plates and 49 prints (47 before rivets; 56 without pooling). The starter
    bay gains one small plate (two cross-frames).
  - Placed, the mirrored start half fills exactly the space the old one did (tested), so brackets, latches,
    cross-frames and keys are unchanged.
- The arch style and the corner trusses get no rivets. A corner frame prints its outer (room) face down, because
  its U-ledges must face up. Riveting it would mean printing the ledges as separate glued strips; that's deferred
  until the user has seen the straight trusses.
- **Rivet test strips on the fit test (2026-10-17):** three 40 × 10 mm strips of panel with two rows of heads at
  0.6, 0.8 and 1.0 mm (1/2/3 notches), at the trusses' pitch and height. Bambu prints all three sizes (slow test);
  the print shows size and stringing before whole panels.
- **The concrete pier stands proud of the steel (2026-10-17):** its body and cap rise `pier_relief` (0.4 mm, two
  layers) on the room face, so concrete and steel no longer blend. The raise stops at the top chord's underside.
  It leaves a 3.4 mm strip at the pier centerline flat, because the bracket (or a corner anchor) grips the plain
  3.2 mm pier there and covers that strip anyway. `pier_relief = 0` turns it off.
- **Rivets 0.6 mm (2026-10-26):** from the fit-test strips, the 0.8 and 1.0 mm heads didn't come out smooth and
  0.6 did. `rivet_d = 0.6`.


## Amendments (2026-10-26): cross-frames grip the panels

- **The first printed bay's cross-frames were "way loose"** on the panels: their slots used the general slide fit
  (0.20 mm over the 3.2 mm panel). They should stay up on their own, with glue as the backup. The slots now have their
  own fit, `fit_cf = 0.05`, and the walls beside them stay `cf_wall` thick. Nothing on the panels changed, so a bay
  printed earlier only needs new cross-frames.
- **Clip coupon** (`build cf-clip-test`, out/cf_clip_test): the top of a cross-frame at `CF_FITS` 0.0 / 0.05 / 0.10
  (1 / 2 / 3 notches on the bottom edge). Push each up onto a printed bay's panels at a post and pick the one that
  stays put. `fit_cf` is the middle one until the coupon says otherwise.
- **Press fit (2026-10-26, clip coupon 1):** of 0.0 / 0.05 / 0.10, the 0.0 clip stayed in place but "didn't fit quite
  as tight as I hoped". The second coupon is 0.15 / 0.10 / 0.05 mm *narrower* than the panel (`CF_FITS`, 1-3
  notches), and `fit_cf = -0.10`, its middle one.
- **Clip 2 picked (2026-10-26):** the user chose the 0.10 mm press fit from the second coupon. `fit_cf = -0.10`
  stays.

## Amendments (2026-10-27): a seventh cross-frame at mid-bay

- **A cross-frame straddles the mid-bay splice** too, so each bay has seven: three per half at the posts and one
  centered on the joint. The user tried one on the first printed bay: "this actually locks the keystone in". Its
  slots press over both panels' keystones as well as the panels. It's the same part as the post frames (every frame
  in these bays is 57.15 mm deep), seated in a `rib_notch`-deep notch split between the two halves so it stays
  centered. Rivets keep clear of it like at the posts (`layout.frame_us`). The arch style keeps its crown block bare.
- **Clash checks vs. press fits:** with `fit_cf < 0` the frames overlap the panels on purpose. `assembly.clashes`
  checks them line-to-line, and `assembly.press_fits` lists the planned overlaps (a test holds them to frames on
  panels and keystones).
- A bay printed before this has rivets and no notch at the splice. Shave the few heads under the frame, and it rides
  1 mm low without the notch.

## Amendments (2026-10-27): corners in the section kits

- `build sections` also writes the corners as kits: `corner_inside` (printed 3×: back-left, front-left,
  front-right) and `corner_bridge` (1×), each with its PETG plates and white PLA cleat plates, plus the `rod_jig`.
  The run sections never held corners, and the only corner file was the MakerWorld one, built before the tighter
  pier slot.
- **A run starts and ends at corners:** the corner's rod anchor holds the run's end pier, so a first bay has no
  bracket at its corner end. To hang a first bay before its corner, print `spare_bracket` (the same bracket) for
  that end, and swap it out when the corner goes up.
- Facing the wall, a run's first bay sits at its right-hand corner and its bays go leftward (run x runs right to
  left as seen from the room).
