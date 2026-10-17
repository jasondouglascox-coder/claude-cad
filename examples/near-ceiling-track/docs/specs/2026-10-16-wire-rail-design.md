# Stainless wire rail: curve test piece — design spec (2026-10-16)

Can the commercial Code 100 rail be replaced by 304 stainless wire on a printed gray web, at a fraction of the
cost? This spec covers the **curve test piece** that answers it on the real corner radius. Commercial rail
stays the default until the test piece passes.

## Decisions
- **Wire: 16 AWG (0.0508", 1.29 mm) 304 stainless**, set as `wire_d` from caliper readings.
  - A scratch study compared 14 and 16 AWG with RP-25 wheels. A round railhead lets the flange touch high on
    the wire's shoulder, not at a vertical face. The contact angle is about 62° on 14 AWG and 70° on 16 AWG,
    against about 90° on real rail. Nadal's flange-climb limit (μ 0.3) is about 1.0 for 14 AWG, 1.35 for
    16 AWG and 3+ for real rail. Deep vintage flanges reach lower on the wire and do much better (75–90°).
  - 16 AWG is also closer to a Code 100 head (0.045"). The cost is about 1.6× the resistance of 14 AWG, about
    0.17 Ω/ft per rail. The run already has a solder gap every 16" bay, so the feeder spacing is fine.
  - Square wire would act like real rail, but none could be found.
- **Gauge: wire equators `gauge` (16.6 mm, 0.6535") apart**, the same as today's track. Deep vintage flanges reach
  the equator and feel exactly today's gauge. RP-25 flanges touch higher up, where the wire is narrower, and
  feel about 0.659", inside S-3.2's 0.649–0.661".
- **Rail top unchanged** at `rail_top` (5.34 mm above the tie underside). The wire's top is the rail top.
- **Keep-outs, unchanged from today's track:**
  - Gauge side: nothing within `flange_depth_max` (1.6 mm) of the rail top, for `flange_depth_max` inboard of the
    gauge face.
  - Field side, under the tread: nothing above 0.008" below the wire top, out to the RP-25 tire width + 0.010".
  - `wire_rail.check_envelopes` proves both on the 2D profile, and a 3D wheelset clash test proves them on the
    curve.
- **Profile (gray web on the brown runner):**
  - A cradle of radius `wire_d/2 + wire_seat_fit` touches the wire's bottom.
  - The **field lip** rises to the highest fine-layer boundary under the tread keep-out (5.12 mm, 0.22 mm under the
    wire top). It is two nozzle lines (0.9 mm) wide at the top, with a vertical outside face.
  - **No gauge lip.** The 16 AWG wire is shallower than the 1.6 mm flange keep-out, so there's no room for a wall
    beside it. On the gauge side, a step two lines wide sits one layer under the wire, then the low shelf. Flange
    forces always push a rail outward, toward the field lip. Glue holds the gauge side, so clamp or tape the wire
    while the glue cures.
  - The wire is held with glue, or heat-seated. At about 0.0004" of interference, a snap isn't possible
    (see the study).
- **Fine layers: the test plates print at 0.08 mm layers (0.16 mm first layer).** At 0.2 mm layers the cradle and
  lips can't be formed: the wire bottom sits only 0.31 mm under the flange keep-out. The brown/gray seam stays at
  `tie_h` (2.4 mm = 0.16 + 28 × 0.08), so there is one color change. The plates' project settings carry the
  layer height, so Bambu Studio opens them ready.
- **Test piece:** an 18° arc of the corner radius `curve_r` (21.7"), one corner span.
  - Brown ties and runners, gray webs, a jigsaw tab on each runner (male at the end, socket at the start).
  - Identical pieces chain, and 5 make the full 90° corner.
  - Plates: `wire_curve_single` (1 piece) for seating the wire, and `wire_curve_corner` (5 pieces) for running a
    train.
  - The wire runs continuously over the joints. The gray web stops over each socket, so it never prints over air.

## Cost (2026-10-16, from the model and Bambu Studio)
- The loop is 37.8 ft of track centerline, so the two rails take about 76 ft of wire: one 100 ft spool.
- Gray plastic: the web slices at 3.8 g per foot of track (both rails), against about 0.9 g/ft for today's tie
  plates. That's about 110 g more for the loop, about $1.65 at $15/kg.
- Print time is the real cost. The single piece takes 77 min at 0.08 mm layers. Printing every deck at 0.08 mm
  roughly doubles the deck print time, unless only the gray band prints fine (a height-range layer setting).
- Also needed: glue (CA or epoxy), and an acid flux for soldering feeders to stainless.

## Tests (each written before its code)
- The profile clears both keep-outs, and a profile with its lip raised fails the check.
- RP-25 wheels feel a gauge inside S-3.2. A `flange_depth_max` flange keeps play both ways.
- Each piece is printable on the fine-layer printer, watertight, with every top on a layer. The gray never sits
  over air, and there is one seam at `tie_h`.
- The wire seats sit at `curve_r ± (gauge/2 + wire_d/2)`, and the wire top is at `rail_top`.
- Two chained pieces don't clash and their tab fills the socket. Five make 90°.
- RP-25 and `flange_depth_max` wheelsets on the curve, flanging both ways, touch no plastic.
- Plates fit the bed, open brown and gray in the slicer, and slice at 0.08 mm with the swap at `tie_h` (slow).

## Open items
- Measured wire diameter (several points along the spool) → `wire_d`.
- Retention: glue vs heat-seat, from the single-piece print.
- A running test on the 5-piece corner with the longest train, pulled and pushed, RP-25 and vintage cars.
- If it passes: the straight ladders and corner decks get the web, and the main plates need fine layers in the
  gray band (a height-range layer setting) so whole runs don't print at 0.08 mm.

## Amendments
- **2026-10-16, after the first slice and an independent review:**
  - Field lip widened from one nozzle line (0.4 mm) to two (0.9 mm). Bambu's classic walls dropped the one-line lip
    entirely: the G-code stopped at 4.48 mm.
  - The gauge-side wedge under the wire was replaced by the two-line step. Classic walls never printed the wedge.
    Arachne printed it as a 0.34 mm bead, up to 0.15 mm into the wire seat (it would widen the gauge) and about
    0.07 mm into the deep-flange keep-out. So the plates stay on classic walls.
  - cadkit fixes found here:
    - **3MF meshes now hold curves to 0.01 mm.** build123d meshes relative to edge size, which put an 18° arc
      0.14 mm off: at chord midpoints the web sat 0.09 mm inside the deep-flange keep-out.
    - **Moved multi-color parts are written where they were placed.** Every two-color part on a plate had been
      written at its first spot, so Bambu refused to slice any plate with two or more ladders, decks or curve
      pieces ("gcode path conflicts").

