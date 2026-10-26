# HO Arch-Deck Ceiling Shelf — Design Spec

Date: 2026-10-12
Status: Draft for review

## 1. Goal

A 3D-printed HO-scale bridge shelf that carries a single track around the office about 12" below the ceiling. It looks like an open-spandrel deck-arch viaduct. The deck is open bridge ties, so from the floor you can see the underside of the trains. Rail is bulk Code 100 nickel silver; everything else is printed.

Success means one prototype bay passes the acceptance tests in §10.3, and the design then repeats along every straight wall with no geometry redrawn by hand.

## 2. Scope

In scope (sub-project 1: straight runs)
- Arch panels, keystones, tie ladders, handrail, cross-frames, wall brackets, end piers, fit-test coupon.
- Parametric generation from one parameter file and one bay list.
- STEP output for Onshape; optional STL/3MF for slicing.

Out of scope (later sub-projects)
- Corners and curves (an 18–24" radius pushes the track about 9" off the wall at each corner).
- Whole-room layout around doors and windows.
- DCC/DC wiring beyond a feeder path through the deck.

## 3. Decisions and why

| Decision | Why |
|---|---|
| Open bridge-tie deck | The user wants to see the train undersides from below. |
| Open-spandrel arch with posts, seen from the room | The user's reference (an arched viaduct shelf). Deepest at supports, where bending is highest. Chunky members print reliably and read from across the room. |
| Track sits directly on a flat top band | User requirement; the track runs straight across. |
| A pier on every stud, 16" bays (set per bay) | Brackets go into studs. Bay length follows the measured stud spacing. |
| Joints locate mechanically; CA adds strength only | User requirement: glue is for strength, never for alignment. |
| Every part prints flat with no supports | Strongest layer orientation for PETG; no support marks on visible faces. |
| Arch splits at the crown with a keystone | A 16" arch won't fit the Bambu A1's 256 mm bed. Prototypical and self-aligning. |
| PETG throughout | Ceiling air is warm; PLA creeps. |
| build123d (Python, OpenCascade) → STEP | The user opens parts in Onshape, which needs B-rep CAD, not meshes. Code-driven, so one parameter change regenerates every part. |

Rejected: the rail-chord deck truss (it can't follow an arch), Forth-style cantilevers (the user preferred the arch), the arched end-view bracket (seen edge-on from the room), and OpenSCAD (mesh-only output).

## 4. Structure

A run is a chain of bays. Each bay is a box made of two identical arch panels, one under each running rail, held apart by cross-frames and capped by tie ladders. Neighboring bays meet at a pier over a wall bracket.

Elevation of one bay (pier to pier):
- Pier: solid, 3" deep below the ties, 1.25" wide, split down the centerline. Each bay owns one half.
- Top band: continuous and level; tie ladders sit on it.
- Arch rib: springs from the base of each pier and rises to 1" below the ties at the crown.
- Posts: vertical, every 2", from the arch rib to the top band.
- Keystone at the crown joins the two printed halves.

Structural check (two PETG panels, crown section only, simple span; conservative):
- 1 lb locomotive at mid-span → under 0.5 mm. Arch action, deeper sections toward the piers, and continuity over piers make the real figure much smaller.
- Member stresses are under 1 MPa. Creep is not a practical concern in PETG at ceiling temperatures.
- Running rails are continuous over piers and keystones and tie the bays together.

## 5. Parts

Quantities are per 16" bay unless noted.

| Part | Qty | Function | Locating features | Print orientation |
|---|---|---|---|---|
| `arch_half` | 4 | Half pier + top band + posts + half arch rib | Crown: dovetail socket for the keystone. Pier end: seats in the bracket notch. Top band: tabs up into the ladder runners. Cross-frame slots at each post. | Flat, panel face down |
| `keystone` | 2 | Joins the arch halves at the crown | Double-ended dovetail; snaps in sideways | Flat |
| `tie_ladder` | 2 (≈8") | Open ties on two runners | Runner slots over the panel tabs; jigsaw ends; tie plates with shoulders set the gauge; spike lips every 4th tie; long tie every 8th | Flat, tie bottoms down |
| `handrail` | 2 (≈8") | Room-side railing | Post pegs press into long-tie sockets | Flat |
| `cross_frame` | 1 per post | H-frame between the panels | Slots over both panels at the top band and the arch rib; sets spacing and squareness | Flat |
| `bracket` | 1 per pier | Holds two pier halves to the stud | Two 3"-deep notches for the panels, with a snap latch; top arm under the ties; vertically slotted wall plate | Flat |
| `end_pier` | 1 per run end | Full-width pier closing a run | Same notch interface as a pier pair | Flat |
| `fit_test` | 1 total | Calibration coupon | Tie-plate grooves, tab/slot, dovetail, each at 3 clearances; one latch | Flat |

Rail: running rails seat in the tie plates and are CA'd every 4th tie. 3 ft rail joints go mid-bay, away from piers.

## 6. Parameters (defaults)

All of these live in `hotrain/params.py`. Every part derives from them.

| Parameter | Default | Note |
|---|---|---|
| `gauge` | 16.6 mm | NMRA HO 16.5–16.8 |
| `rail_height` | 2.54 mm | Code 100 |
| `rail_base_w` | 2.2 mm | Published nominal; calibrated by `fit_test` |
| `rail_head_w` | 1.1 mm | Published nominal |
| `rail_ctc` | `gauge + rail_head_w` (17.7 mm) | Panel centerline spacing |
| `track_offset` | 44.45 mm (1.75") | Wall to track centerline (set by the corners spec) |
| `rail_top_below_ceiling` | 304.8 mm (12") | For the layout line |
| `tie_l × tie_w × tie_h` | 35 × 2.6 × 2.3 mm | 10 ft bridge tie in HO |
| `tie_pitch` | 5.5 mm | 2.9 mm see-through gaps |
| `tie_plate_h` / shoulder | 0.3 / 0.6 mm | Gauge-setting shoulders |
| `spike_lip_every` | 4 | Ties |
| `long_tie_every` / `long_tie_reach` | 4 / 28 mm from track center | Handrail posts, one spacing (~22 mm) along the whole run |
| `panel_t` | 3.2 mm | 16 layers at 0.2 mm |
| `pier_depth` | 76.2 mm (3") | Below tie underside |
| `crown_depth` | 25.4 mm (1") | Below tie underside |
| `top_band_h` / `rib_h` / `post_w` | 6 / 6 / 3 mm | |
| `post_pitch` | 50.8 mm (2") | |
| `pier_w` | 31.75 mm (1.25") | Two halves |
| `bay_len` | 406.4 mm (16") | Overridable per bay; 203.2–480 mm (8–18.9") so every arch half and tie ladder fits the bed with margin |
| `bracket_t` | 6 mm | |
| `bracket_reach` | ≈ 49 mm | Wall to room-side tie end; solid web when the arm is under 20 mm |
| `bracket_slot` | ±6.35 mm (±¼") | Vertical leveling |
| `handrail_h` / `handrail_offset` | 19 mm / 25 mm | Above rail top / from track center |
| `fit_slide` | 0.20 mm | Calibrated |
| `fit_snap` | 0.05 mm | Calibrated |
| `bed` | 256 × 256 mm | Bambu A1 |

`hotrain/layout.py` holds the run as a list of bay lengths (measured stud-to-stud distances) plus run-end markers.

## 7. Joints and fits

- **Tab/slot** (panel to ladder): `fit_slide` clearance; through-slot with the tab flush.
- **Dovetail** (keystone to arch half): `fit_snap`; inserted sideways, perpendicular to the panel; CA after dry fit.
- **Cross-frame slots**: `fit_slide`; slot width = `panel_t + fit_slide`.
- **Bracket notch**: `fit_slide` side clearance. A flexing latch printed in the bracket plane, so it flexes in the strong direction, catches a ledge on the pier.
- **Tie plate**: groove width = `rail_base_w + fit_slide`; spike-lip overhang 0.3 mm over the rail base flange; the rail slides in from the end.
- **Jigsaw** (ladder to ladder): `fit_snap`; pressed down.
- **Handrail pegs**: `fit_snap` press fit into the long-tie sockets.

## 8. Assembly and mounting

1. Mark the studs and measure stud-to-stud distances into `layout.py`. Snap a laser line at bracket-top height (rail top − rail − tie − plate). Level to the laser line, not the ceiling.
2. Screw one bracket per stud (#6 × 1½" wood screws through the slots). Set each top arm on the line and check three at a time with a straightedge.
3. On the bench: arch halves + keystones → panels; add cross-frames; check square and flat; then CA.
4. Drop the bays into the brackets. Neighboring pier halves share a notch; the latch clicks. Bays are not glued to brackets, so they stay removable.
5. Press the tie ladders onto the panel tabs, with joints staggered from the panel joints.
6. Solder feeders under the rail. Lay 3 ft rails into the tie plates under the spike lips, with joiners mid-bay and a small expansion gap. Check with an NMRA gauge, then CA every 4th tie. Feeders drop between the ties into the hollow between the panels and exit behind a pier.
7. Press in the handrails. Test-run before starting the next wall.

## 9. Software

```
HOTrain/
  pyproject.toml          uv project, Python 3.12, build123d pinned
  hotrain/
    params.py
    layout.py
    lib/profiles.py       rail profile, tie plate, spike lip
    lib/joints.py         tab/slot, dovetail, jigsaw, latch
    parts/                arch_half, keystone, tie_ladder, handrail,
                          cross_frame, bracket, end_pier, fit_test
    assembly.py           one assembled bay, parts positioned in place
    build.py              CLI
  tests/                  pytest
  out/                    generated, gitignored
  docs/specs, docs/plans
```

CLI (`uv run python -m hotrain.build ...`)
- `all`: every part type at default bay length → `out/step/<part>.step`
- `bay N`: the part set for bay N of `layout.py` at its length
- `assembly`: `out/step/bay_assembly.step`, a positioned multi-part assembly for review in Onshape
- `fit-test`: the calibration coupon
- `--mesh`: also write STL/3MF for slicing
- `--preview`: SVG line-drawing previews in `out/preview/`

Every exported part sits in its print orientation (flat on Z=0) so it can go straight to Bambu Studio, which also imports STEP.

## 10. Verification

### 10.1 Automated (pytest)
- Every part is a single valid solid.
- Every part's footprint fits the 256 × 256 mm bed with a 5 mm margin, at the maximum bay length.
- Gauge: on the generated ladder, the two tie-plate groove centerlines are `rail_ctc` apart within 0.01 mm, and each groove is `rail_base_w + fit_slide` wide.
- Assembly: no unintended interference between parts in `assembly.py` (pairwise boolean intersection volume ≈ 0, excluding designed press fits).
- Mating features: slot widths and dovetail clearances match the `fit_*` parameters.

### 10.2 Fit-test print (≈20 min)
The user test-fits real rail and parts in each clearance variant and picks the best ones; we update `params.py`.

### 10.3 Prototype bay acceptance
One 16" bay plus two brackets, ladders and handrail, mounted. It passes when:
- An NMRA gauge passes along the full length.
- A 1 lb weight at mid-span sags less than 0.5 mm.
- The heaviest locomotive and longest car make 20 passes with no derailment and no visible bounce.
- A car tipped toward the room is caught by the handrail.
- After a night under the weight in a warm spot, there's no added sag.

Only after this passes: batch-print the run.

## 11. Estimates (rough; replaced by slicer numbers after the prototype)

- About 135 g PETG and 6–8 h of print time per bay.
- A 48 ft run (about 36 bays) is about 5 kg PETG and 96 ft of Code 100 rail (32 three-foot sticks plus spares).

## 12. Risks and open items

- **Real rail dimensions** vary by brand; the fit test calibrates them.
- **HO-scale detail on FDM**: tie plates and spike lips are near the limit of a 0.4 mm nozzle. Fallback: drop the spike lips and rely on the shoulders plus CA.
- **Irregular stud spacing** near doors and corners: bays up to 18.9"; beyond that, an intermediate drywall-anchored pier.
- **Thermal expansion** (nickel silver vs PETG): handled by gaps at the rail joiners and bays that aren't glued to brackets.
- **Filament color**: the user's choice; it doesn't affect the design.

## 13. Amendments from implementation planning (2026-10-12)

- `tie_plate_h` is 0.4 mm (two 0.2 mm layers), not 0.3.
- `end_pier` quantity is 2 per run end (one per panel).
- Bay length limits: 203.2–480 mm (8–18.9"); 480 keeps the tie ladder that spans a pier, including its jigsaw tab, on the bed. The build refuses anything outside that with a clear error.
- Keystone is a bow-tie (butterfly) key pushed in from the panel face.
- Cross-frames locate along the track with a 1 mm notch under the arch rib at each post.
- Bracket wall plate is a 30 mm L-flange printed as part of the bracket, with two vertical screw slots.
- Latch: a flexing finger in the bracket's room-side slot wall hooks into a small window through the pier.
- Code layout: `hotrain/joints.py` and `hotrain/checks.py` replace `lib/profiles.py` and `lib/joints.py`.
- CLI: `parts` (whole run plus `out/manifest.csv`) and `check` (interference) replace `bay N`.
- Bracket screw slots sit 5 mm past the plate (about 8 mm from the stud centerline) so screws land in the middle of the stud.
- STEP product names are part types (e.g. `arch_half_406.4mm`, `bracket`), matching `out/manifest.csv`.
- Track moved to 1.25" from the wall (was 2.5") to save plastic; the bracket becomes a solid web about 1.9" deep.
- Flange is 26 mm wide; screw slots sit centered on its exposed tab. Hang each bracket with its screw line on the stud center (the pier then sits about 13 mm to one side; bay lengths are unchanged).
- `build assembly` and `build all` also write `demo_two_bays.step`: two default bays sharing one bracket, showing how units join.
- Handrail posts sit on every 4th tie with one spacing along the whole run, across piers and onto the end piers. Each bay holds a multiple of 4 ties (pitch ≈5.6 mm at 16"). Handrail pieces are split at the post nearest each ladder joint: each piece owns its first post and the previous piece's bars stop 0.5 mm short of it.
- `build plates` packs parts onto 256 mm A1 plates (MaxRects, 3 mm gaps, two arch halves nested head-to-tail). Each bay = plate A (2 arch halves, 3 cross-frames, keystone, crown ladder + handrail) and plate B (same + bracket, pier-crossing ladder + handrail); `run_ends` = 4 end piers, the extra bracket, the first ladder + handrail. Identical plates are listed once with a quantity in `out/plates.csv`; each plate is written as STEP and 3MF.
- Rail stays Code 100: it suits vintage equipment with deep ("pizza-cutter") flanges. Spike lips are on the outside of each rail only; the gauge side stays clear to `flange_depth_max` (1.6 mm) below the rail top.
- Bus wiring: each cross-frame has a finger reaching to the bracket flange face, forming an open-top cradle (floor at Z = −4 mm, 11.5 mm wide, wall-end lip) for a 16 AWG pair along the wall. Each bracket has a 7.8 × 5 mm pass-through in front of its flange. Wires can be laid in from above after assembly; feeders drop between the ties.

## 14. Amendments (2026-10-16)
- Exploring 16 AWG stainless wire rail on a printed gray web in place of commercial Code 100 rail: see
  `2026-10-16-wire-rail-design.md`. Commercial rail stays the default until the curve test piece passes.
- Every brown/gray plate leaves Bambu's prime tower corner free (cadkit packs multi-color parts around the slicer's
  `tower_keepout`, on the A1 template x 31-78, y 210-257 mm). Before this, Bambu refused all five two-color plates
  and the starter's ladder plate ("gcode path conflicts" with the tower). The plate list didn't change. A slow test
  slices every two-color plate.
- Every kit is also written as one project with every plate (`near_ceiling_track`, `starter`, `wire_test`), and
  `build makerworld` slices five print profiles for one MakerWorld model: starter bay (deck truss, arch), corners
  (pony, bowstring), wire-rail test.

## 15. Amendments (2026-10-26): fit-test results

- **Keystone: variant 1, no clearance** (`fit_key = 0.0`; 0.05 and 0.10 were loose). The key fits tight when its bed
  side meets the panel's bed side, and loose flipped. The README says to match bed side to bed side.
- **Tab slots: variant 1, 0.10 mm** (`fit_tab`; 0.10 and 0.20 both fit, and the user chose the tighter).
- The keystone, tab slots and (below) the pier slot get their own fits. The rail grooves, cross-frames and rods
  keep `fit_slide` (0.20) until their samples are tried: the tie-plate grooves need the rail, the rod seats a 1/4"
  rod.
- **Latch:** the first coupon's pier stub fell out of the fork. A latch coupon then tried the spring slot at 40, 25,
  15 mm and none: no slot was best, but still a little loose. So the brackets (and the corner anchors' latches)
  now have **no spring slot** (`latch_finger_len = 0`), a **tighter pier slot** (`fit_pier = 0.10`, from 0.20) and a
  **longer hook** (`latch_engage = 1.2`, from 0.8). PETG gives enough to unlatch by bending the bracket back. The
  latch coupon now tries the hook at 1.0, 1.2 and 1.4 mm (1-3 notches) to confirm.
- **Latch hook 1.4 mm (2026-10-26):** on the second latch coupon the user found variant 3 "perfect"
  (`latch_engage = 1.4`).

