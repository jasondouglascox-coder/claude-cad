# Cat decals: spec

## Intent

The user's wife wants lots of little cats doing different things, cut from black vinyl on their Silhouette Cameo
(a Pro, with a 24" × 24" mat). This is not a 3D print. The cutter follows outlines only, so each cat is a solid
silhouette that has to read from its shape alone.

## Decisions

- **Format: DXF.** Silhouette Studio's free Basic Edition opens DXF, but SVG needs Designer Edition. The files are R12,
  with every outline and hole a closed POLYLINE, so each one is a single cut. R12 has no units field, and Studio is known to guess a DXF's
  size wrong, so the sheet (in inches) carries a 1" test square to measure.
- **Poses (12):** sitting, from behind, lying, yarn (paw on a wound ball, loose end trailing), stretching, arched,
  asleep (tail wrapped, cut free of the body by a groove), walking, washing (paw up, elbow out), pouncing, reaching,
  peeking (head and paws over an edge, tail hanging below). The user named lying, sitting and playing with yarn. The
  rest are Claude's choice, drawn from common cat silhouette sets.
- **Size:** 3" on the longer side (Claude's guess at "little", which the user accepted). Wide poses therefore come out
  low. One parameter changes it.
- **Weedable:** nothing narrower than ⅛" (opening test). Holes at least 0.1" wide and 0.03 sq in. Interior detail
  only as holes big enough to pick out, such as between the legs, the yarn's winding, or the washing cat's elbow.
- **Sheet:** one of each pose (amended below), a ½" margin, and ½" between cats. Rows stand on a common baseline, slid
  together by true shape distance so tails tuck under neighbours, and the group sits at the mat's top edge.
- **Drawing:** poses are built in Python from ellipses, tapered spline strokes and two head shapes (profile and
  front), unioned, then closed and opened by small radii, so joins blend and tips round.

## Open

- Check on the real machine how Studio sizes the `_in` file, and record it in `docs/measurements.md`.

## Amendments

- **2026-10-31: one of each, inches only.** The user duplicates and scales cats in Studio, so the sheet carries each
  pose once (plus the test square), ½" apart (was ¼"), across the top of the mat where the Cameo starts. The repeated
  53-cat fill, the `_mm` sheet and the per-pose DXFs are gone: only `out/cat_sheet_in.dxf`.
