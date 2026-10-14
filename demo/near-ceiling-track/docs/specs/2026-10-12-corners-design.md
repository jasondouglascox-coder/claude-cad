# HO Shelf Corners — Design Spec

Date: 2026-10-12
Status: Draft for review
Builds on: `docs/specs/2026-10-12-arch-deck-shelf-design.md` (straight viaduct)

## 1. Goal

Turn the track 90° at every corner of the office with one consistent look: a chain of identical **bowstring arch spans** that carries the train straight in, around a safe curve, and straight out onto the next wall's viaduct. Two aluminum rods run continuously through each corner's deck as the structure. The printed spans locate the rods and look like a bridge; the rods carry the load and rest on a few supports.

Success: a printed inside corner and the alcove bridge corner each carry the heaviest locomotive around at speed with no derailment, no visible sag, and a look that flows from the viaduct.

## 2. The room's corners

| Corner | Count | Shape | Supports |
|---|---|---|---|
| Inside corner | 3 | Two walls meet at 90°; the curve cuts across the corner | Wall anchor on each wall, plus a 6" bracket off each wall partway round. No ceiling. |
| Bridge corner | 1 | The alcove beside the bump-out (top wall to bump-out face, 43.75" / 1111.25 mm). The track skips the alcove: it curves off the top wall onto the bump-out's face line, then crosses the alcove mouth to the bump-out corner. | Wall anchor on the top wall, a 6" bracket off the top wall, one ceiling drop at the end of the curve, and a wall anchor at the bump-out corner. |

Wrapping the bump-out's outside corner directly was rejected: at a safe radius the track would have to sit about 7.7" off both walls, which squeezes the alcove U-turn below 18".

## 3. Decisions and why

| Decision | Why |
|---|---|
| Track moves from 1.25" to **1.75" (44.45 mm)** off every wall | The bowstring's wall-side arch needs ~1¼" from the track center. Applies to the whole run, so every span has one width. |
| One curve radius everywhere: **R = 550.3 mm (21.67")** | Fixed by the alcove: 1 straight span plus 3 straight spans must exactly reach the bump-out corner. Inside corners reuse it, so curve parts are shared. Safe for most vintage HO (18" is the usual minimum). |
| Every span is the same length, **s = 2R·sin 9° ≈ 172.2 mm (6.78")** | 5 curve spans of 18° each, and straight spans at the same length. One uniform rhythm. |
| Through-bowstring spans (pony arches, no top bracing) | The look the user chose. Arches clear 60 ft cars on the curve. |
| Two **¼" × 6 ft aluminum rods** per corner, continuous through every span | User's design: strength is in the rods, the prints locate them, few supports. Two rods also resist twisting of the curved girder. |
| Ceiling drop = stainless picture-hanging cable plus adjustable gallery grippers | Doesn't stretch or creep like fishing line; height is adjustable for leveling. |
| Every part prints flat on the A1 | Same rule as the viaduct. |

## 4. Geometry

### 4.1 Common

- Track centerline offset from walls: `o = 44.45 mm`.
- `R = (D − o) / (1 + 6·sin 9°)`, where `D = 1111.25 mm` (the alcove width), giving 550.3 mm. Stored as a parameter, computed from `D`.
- Span length `s = 2R·sin 9°` = 172.2 mm. Straight spans use the same `s`.
- Portals P0…Pn sit between spans. Curve portals lie on the arc, 18° apart. The track curves smoothly through the curve spans, straying up to `s²/(8R)` ≈ 6.7 mm from each span's chord. Each span's frames are centered on the line that best fits the track, so the track strays about ±3.4 mm either way.

### 4.2 Inside corner (7 spans)

P0 sits on wall A, one span before the curve. Then P1 (curve start, tangent to wall A's offset line), P2…P5 at 18° steps (P5 = 72°), P6 (curve end, tangent to wall B's offset line), and P7 one straight span later on wall B.

| Portal | Distance from nearest wall (track center) | Support |
|---|---|---|
| P0, P7 | 44.45 mm | Wall anchor |
| P1, P6 | 44.45 mm | none (rod continuous) |
| P2, P5 | 71 mm | none |
| P3 (36°), P4 (54°) | 150 mm (5.9") | 6" bracket: P3 off wall A, P4 off wall B |

Rod spans between supports: P0–P3 (3 spans), P3–P4 (1), P4–P7 (3). Rod length is about 7·s plus the anchor ends, roughly 1.3 m (51"), so each inside corner uses two 6 ft rods. The whole room needs 8 rods: 3 inside corners × 2, plus the bridge corner's 2.

### 4.3 Bridge corner (9 spans)

P0 sits on the top wall, then 1 straight span to P1 (curve start), 5 curve spans to P6 (curve end, on the bump-out's face line), then 3 straight spans to P9 at the bump-out corner (the viaduct continues down the bump-out face from there).

| Portal | Support |
|---|---|
| P0 | Wall anchor on the top wall (also takes the last top-wall viaduct pier) |
| P3 (36°, 150 mm off the top wall) | 6" bracket off the top wall |
| P6 (curve end, ~595 mm off the top wall) | Ceiling drop: two cables, one each side outside the arches |
| P9 | Wall anchor at the bump-out corner (also takes the first bump-out viaduct pier) |

Rod spans: P0–P3, P3–P6 and P6–P9, 3 spans each (~517 mm). Outer rod about 1.65 m and inner about 1.55 m, both under 6 ft.

### 4.4 Structural check (two ¼" 6061 rods, EI ≈ 1.1×10⁷ N·mm²)

- Worst case, a 1 lb locomotive at the middle of a 517 mm simple span: about 1.3 mm. Rod continuity over supports and the printed deck roughly halve that, to under 1 mm.
- Inside corners have spans of 517 mm or less, so they come out the same or better.

## 5. Parts

All print flat. "Curve" and "straight" variants share one code path, with the curve as a parameter.

| Part | Per inside corner | Bridge corner | What it is |
|---|---|---|---|
| `bow_deck` (straight / curve) | 2 / 5 | 4 / 5 | Open tie ladder for one span. Ties are radial on the curve. Tie plates set gauge along the true curve. Two rod channels underneath follow the true rod arcs and snap over the rods. Edge beams along the frame lines have tab slots. Jigsaw ends join the neighbors. |
| `bow_frame` (straight / curve-inner / curve-outer) | 4 / 5 / 5 | 8 / 5 / 5 | Bowstring side frame: bottom chord, arch rib (crown ~38 mm above the rail top), vertical hangers about every 29 mm, end posts. Tabs into the deck edge beam. Curve frames are shorter (inner) or longer (outer) by `w·tan 9°` per end so neighbors meet at the portal. |
| `floor_beam` | 8 | 10 | Transverse beam under each portal. Snaps under both rods and carries both decks' ends. Its outboard ends have cable eyes (used only at the ceiling drop) and a clip for the bus wire. |
| `rod_anchor` | 2 | 2 | Wall bracket at the ends of a corner. Wall flange (screw slots), sockets for both rod ends, and on the viaduct side the standard pier slot plus latch for the adjoining viaduct bay. |
| `deep_bracket` | 2 | 1 | Wall bracket reaching 6" to a portal; its top saddle snaps under both rods where they cross its plane. |
| `drop_clamp` | — | 1 pair | Cable termination that clips onto the floor beam eyes; the cable runs up to a ceiling hook. |
| `rod_bend_jig` | 1 per build | | A ~200 mm arc at the rod radius, clamped down; bend the rod progressively against it. |

## 6. Dimensions (new parameters)

| Parameter | Default | Note |
|---|---|---|
| `track_offset` | 44.45 mm (1.75") | Changed from 31.75 mm |
| `alcove_w` (D) | 1111.25 mm | Measured |
| `curve_r` | derived | 550.3 mm |
| `bow_span` | derived | 172.2 mm |
| `bow_frame_y` | 31.5 mm | Frame centerline from track center. Car half-width 20 + 60 ft car overhang ~5 + chord stray 3.4 + half frame 1.6 + clearance 1.5. |
| `bow_rise` | 38 mm | Arch crown above the rail top |
| `bow_hanger_pitch` | ~29 mm | 6 panels per span |
| `rod_d` | 6.35 mm (¼") | Channel bore = rod_d + `fit_slide` |
| `rod_y` | 18 mm | Rod centerlines from track center |
| `car_len_max` | 60 ft | Sets overhang clearance |

## 7. Joints

- **Rod channels:** C-section, mouth down, printed mouth-first (it prints without supports). The rod snaps up into it. CA is optional.
- **Deck to deck:** jigsaw at each portal (radial line), the same as the viaduct ladders.
- **Frame to deck:** three tabs per frame into the edge-beam slots.
- **Deck ends to floor beam:** both neighboring decks seat in a shallow pocket on the beam.
- **Corner to viaduct:** the rod anchor carries a standard pier slot and latch, so the adjoining viaduct bay drops in as it would onto a normal bracket. Rails and the bus are continuous across.

## 8. Wiring

The bus leaves the viaduct's wall-side cradle at each corner anchor and runs under the corner deck in clips on the floor beams, between the rods, then rejoins the cradle at the far anchor. Feeders drop between ties as usual; the corner gets one feeder pair at its middle.

## 9. Install order

1. Snap level lines on both walls, mark the anchor and deep-bracket positions from the generated layout sheet, and fit the ceiling hook (bridge corner only).
2. Bend both rods on the jig and dry-fit them through the floor beams.
3. Mount the anchors and deep brackets. Lay the rods in, snap on the floor beams, then the decks, then the frames.
4. Hang the cables, set height with the grippers, and level against the viaduct.
5. Bend and lay the rail, check gauge, glue, then wire.

## 10. Verification

### Automated
- Every part is printable (`printable_problems` == []).
- Corner assembly has no clashes, including with the viaduct bays on both sides.
- A 60 ft car envelope swept along the curved track clears every frame.
- Tie-plate gauge holds along the curve.
- Rod-sized bodies along the true rod arcs clear everything except the channels they snap into.
- The bus envelope clears everything.
- Packed plates fit the bed.

### Physical
- Bend one rod and check it against the jig, then against the deck channels.
- Print one curve span plus two floor beams and test-fit on a rod.
- Build one inside corner and run the acceptance tests from the viaduct spec, with a 60 ft car included.

## 11. Out of scope

- Mounting points at room scale (where studs fall relative to corner anchors). The anchors may land between studs; they then use drywall toggles, since the loads are small.
- Room layout tooling (wall lengths to bay list): next sub-project.

## 12. Confirmed (2026-10-12)

- Alcove width is 43.75", possibly up to 44". The bump-out `rod_anchor` has ±9.5 mm (⅜") of slotted adjustment along the track, so the corner fits anywhere in that range.
- The ceiling is flat. Straight runs keep the rail 12" below it; corners may sit lower if needed, though they don't need to (the arch crown is ~1.5" above the rail). The rail is 2 ft above the door tops.
- The longest car is 60 ft (`car_len_max`).

## 13. Amendments from implementation and review (2026-10-12)

- **Floor beams.** These sit at internal portals only (n − 1 per corner); the anchors hold the rod ends. Standard beams stop 2.5 mm short of the wall, which matters at the curve's ends. Only the beam at a ceiling drop (`floor_beam_drop`) reaches past the arches and has cable eyes. Gallery-cable grippers hook straight into the eyes, so there is no printed drop clamp.
- **Bores.** Floor beams and anchors have loose closed bores (`fit_thread` 0.6 mm) so they slide along hand-bent rods. The bus hook sits at u = rod_y + 16, clear of the deep brackets.
- **Install order** (replaces §9 steps 2–3):
  1. Bend both rods.
  2. Slide on, in order, the entry anchor, every floor beam, and the exit anchor.
  3. Screw the anchors and deep brackets to the walls with the rods in place.
  4. Snap the decks down onto the rods, then the frames.
- **Rods** run 12 mm (`rod_tail`) past each anchor, so an alcove up to 44" still keeps them engaged. Cut lengths are in `out/corners_layout.csv`.
- **Bending jig** is a **gauge**, not a form. 6061 springs back a lot at R ≈ 550 mm, so bend a little past the gauge by hand, let it spring back, and check against it. Fixing the rods into the deck channels pulls them the last bit into shape.
- **Runner snap mouth** is 0.88 × rod diameter (`rod_mouth` 0.24). The fit test now includes three rod-snap samples (`SNAP_MOUTHS`).
- **Frame tabs** reach the bottom of the edge beam (full slot depth), so a frame can lean less than 1 mm at the crown.
- **Deep bracket:** 70 mm deep, two screw slots, and a 7 mm knee brace rising ~30° from a gusset on the flange.
- **Viaduct runs ending at a corner** (`layout.RUN_ENDS`, `layout.CORNER`) get no end bracket and no end piers, and their deck stops at the anchor.

## 14. Amendment: pony truss side frames (2026-10-13)

- **Style.** Corner side frames are now a **Pratt pony truss** like the Atlas through truss, minus the overhead
  bracing. They have inclined end posts, a horizontal top chord 42 mm above the rail top (`truss_rise`),
  6 panels (`truss_panels`), verticals, diagonals sloping down toward mid-span, and small gussets at the joints.
- **Why no overhead bracing.** HO cars need about 75–80 mm of headroom. On 172 mm spans that makes each truss
  roughly half as tall as it is long, a chunky "tunnel of boxes" across the alcove, and it needs new
  bracing parts plus a height-clearance check. The pony truss keeps the photo's look for a drop-in swap.
- **Unchanged.** Frame thickness, tabs and deck slots, placement at ±`bow_frame_y`, rods, decks, floor beams,
  anchors and plates are all the same. The 60 ft car sweep (50 mm tall from rail top + 3) already covers the truss height.
- **Bowstring kept.** Set `corner_style="bowstring"` to get the old frames.

## 15. Amendments (2026-10-13): deck colors, bus side, ceiling line

- **Corner deck, flat (supersedes the two-color edge-beam deck).**
  - Each deck is one flat printable part like the straight tie ladder: ties plus two strips under the rails.
  - It prints tie undersides down. Brown ties and strips, then gray tie plates, shoulders and lips on the top layers:
    **one color change** per print and no supports.
  - It **rests on the two rods**, which sit in shallow part-circle grooves under the ties for alignment.
    `rod_cover` is now −0.8, so each rod top sits 0.8 mm into its groove and the rods are about 1.8 mm higher.
    The floor beams' rod bores now open at the top as cradles. The rod channels and deck edge beams are gone.
  - The fit-test coupon swaps the rod-snap samples for three rod-groove seats (`ROD_SEAT_FITS` 0.1/0.2/0.3).
- **Trusses hug the deck.**
  - Two inward ledges on each truss's bottom (`frame_ledge` 2.5 deep: `frame_ledge_lo` 1.6 under the ties and
    `frame_ledge_hi` 1.2 over them) form a U. The tie ends slide in to `fit_slide` from the truss's inner face, then glue.
  - The outer face runs down past the deck edge, so the outside reads solid gray.
  - At each end the bottom steps up by `frame_ledge_end` 3.6, and the truss sits on the floor beam. The step locates the span.
  - The trusses print outer face down, so the U opens upward. The frame tabs and deck slots are gone.
    `corner_assembly.frame_location` turns each truss so its ledges face the track.
- **One part in CAD.** `hotrain.paint` fuses a two-color part into one solid and writes face colors into the STEP, so
  Onshape shows each deck and ladder as a single part with gray tie plates. Viewers split them back into colored bodies,
  and plates/3MF carry the separate bodies for the printer.
- **Bus hook on the wall side.** `floor_beam.bus_u` is now −(rod_y + 16). It was +u, toward the curve center, which is the room side.
  On that side the wire crosses the deep brackets' 5 mm top arm, so the hook now hangs `bus_hook_drop` 11 mm below the beam and the
  wire passes about 2 mm under the arm. `floor_beam.bus_z` gives the wire height.
- **Ceiling drop → braided line + ceiling cleat.**
  - The bridge corner hangs from 50 lb **braided** (Dyneema/PE) line, not monofilament, which creeps.
  - The line wraps 2–3 tie ends just outside a truss's edge beam (`line_u`), `line_inset` into the span past the ceiling portal.
  - It ties off on a small **horn cleat** (`ceiling_anchor`), 42 × 7 mm and 6.5 mm below the ceiling, held by two #6 pan-head
    screws outside the horns. The line takes a turn round the stem, figure-eights over the horns and finishes with a locking hitch.
    The gap under each horn narrows from 2.0 mm at the tip to 0.7 mm at the stem, so the braid jams there.
  - Everything is on the room side, so the corner can be re-levelled with the screws in. The cleat prints on its side with no supports.
  - All floor beams are now standard. `floor_beam_drop` and the picture cable are no longer used, and the layout sheet's rows
    are now "ceiling anchor".
