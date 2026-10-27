# Lily of the valley wall flower: design spec (2026-10-26)

Reference (`docs/references/`, kept local: not ours to publish): the user's photo of a lily of the valley sprig. A
pale-green stem arches up and over to the right, with small leafy bracts; white bells hang from curved green
pedicels. Each bell is rounded, with a flared rim of six scalloped lobes curling back. A broad leaf sits behind.
Printer: Bambu A1 + AMS lite, 0.4 nozzle, 0.20 mm Standard. Hung with the sunflower, rose and peony.

## Goal
The sprig from the photo, about the size of the last flowers (188 mm tall, 70% of the bed), flat back on the bed,
hung on a nail through a hidden keyhole. Green PLA for the sprig, white PLA for the bells.

## Shape (settled with a comparison sheet; the user picked "A, photo sprig")
The options were A (the photo's sprig, no leaf), B (the same with a broad leaf behind and the bells tilted 22
degrees toward you, 1 h 42, 41 g) and C (a stem arching across, seven bells in a row, a slim leaf; 1 h 19, 28 g).

- **Stem:** a Bezier rising up the left and arching over to the right, radius 2.5 tapering to 1.4 mm.
- **Five bells** hanging below it, side-on: each lies in the wall's plane, its apex at the pedicel and its mouth
  down. Along the axis: a rounded shoulder, straight-ish sides widening a little, a slight waist, a flared rim.
  The rim is scalloped into six lobes: the two at the sides curl back in the wall's plane (horns); the two facing
  you reach past the rim, so the bell's lower edge is scalloped from the front. A shallow cone hollows the mouth.
  Bells are 12 mm radius at size 1, 24 mm long, 0.85 as deep as wide; sizes 0.8 to 1.0, smallest at the tip, each clear of the others.
- **Pedicels** from the stem out and up, over and down into each bell's apex; a small pointed **bract** at each
  pedicel's foot.

## Printing without supports
Every part is a tube of vertical sections (`shapes.section`): an ellipse above (what you see), and below it a
fill running in to the bed at 46 degrees or steeper. The ellipse hands over to the fill where its underside gets
flatter than 50 degrees (lobed sections included). From the front only the ellipse shows; the fill is hidden
under it. The bells' mouth hollow is a cone whose roof is far shallower than 45 degrees. Tested: no face overhangs
past 45 degrees except the keyhole roof's 1 mm top (a 7 mm2 bridge).

## Colours: one change, by height
Green below the seam (5.0 mm), white above. The stem's top sits on the seam, the pedicels and bracts under it;
each bell's axis is at 6 mm, so from the front every bell is white and everything else green (tested on the
front view: over 99.5% of the bells' cells above the seam, nothing else above it). The pedicels run in under
each bell's shoulder, hidden.

## Hanging
The keyhole hides under the third bell, the one over the centre of mass: the nail rests 6.6 mm down its axis from
the apex, moved sideways to straight above the printed centre of mass, so the sprig hangs within a degree of plumb.
A 6 mm slot, a 9.5 mm head, a 44-degree roof with 1.2 mm of wall all round, the mouth's hollow included. Nail:
68.3 mm below the sprig's top, 37 mm in from its left edge; a 6-8 mm head about 2 mm off the wall.

## Build
Meshes from the start (peony lesson: B-rep booleans give up on freeform bodies), one `cadkit.mesh` union, the
keyhole cut, slivers collapsed (`Mesh.simplify`), then cut at the seam into green and white bodies. No STEP; the
plate comes with an STL.

## Amendments
- 2026-10-26: Sliced (Bambu Studio): 1 h 08 m, 22.1 g (green 11.4 g, white 10.8 g), one colour change at layer
  25, no supports generated.
- 2026-10-26: Pre-print review (independent agent, every finding probed, most against the sliced G-code). Fixed:
  - **Hangs from its printed centre of mass, not the solid model's.** The thin green parts print solid and the bells
    are 15% infill, so the plastic balances a millimetre left of the solid centroid; with the nail only 15 mm above
    it, that tilted the sprig 3.8 degrees. `hang_point` now uses `Mesh.printed` (new in cadkit: walls and shells solid,
    the rest at infill), which lands within 0.05 mm of the G-code's own centre of mass. A slow test checks the
    sliced G-code's centre of mass (`cadkit.gcode.centre_of_mass`, new): 0.4 degrees.
  - **Keyhole wall:** the head end came within 0.63 mm of bell 3's mouth hollow (the volume test's tolerance hid
    it). The nail moved up the bell from 8 to 6.6 mm below the apex; the test now measures the gap to the air
    (`Mesh.gap`, new): at least `key_wall` all round.
  - **The key bell's pedicel carries the sprig.** A pull straight out from the wall at the foot bends it: 47 MPa at
    1 N before. Pedicels 1.2/1.0 to 1.3/1.2 mm radius, and every fill now stands on at least 0.9 of its top's width
    (`shapes.FOOT`, was 0.25): the height is capped by the seam, so the foot is where the stiffness comes from. Now
    26 MPa at 1 N taking that pedicel alone, the arm to the farthest point (tested against `knock`, `pla_strength`);
    the pedicel below runs into the same bell, so about half that. The wider foot also fixes the pedicels' first
    layer, which the slicer had dropped (0.4 mm wide; now at least two lines).
  - Re-sliced: 1 h 11 m, 23.2 g (green 12.4 g, white 10.8 g), one colour change at layer 25, no supports.

  Accepted as they are:
  - Green shows on the bells from below (11% of the bell at 20 degrees below, 24% at 60), little from the side or
    above: colour by height. Hang it at or above eye level.
  - The front lobe points print about 0.5 mm short and blunter (0.2% of the front silhouette).
  - Eight horn tips start as small separate islands on the bed (about 5 mm2 each) up to 3 mm, then join their bells.
  - Bells 4 and 5 overlap into a double bell at the tip, and pedicels run under the next bell's lobes: as rendered.
  - Not checked: stringing between the bells above the seam (each layer travels between them).
- 2026-10-27: One small cup at the tip. The user found the tip's two overlapping bells (sizes 0.85 and 0.8, 1309 mm3
  shared) looked funky: they read as one odd double cup. Now five bells, the last a single size-0.8 cup hanging
  straight down near the arch's end (0.94 along the stem, 10 mm out), and a test that no two bells overlap.
  Re-sliced: 1 h 06 m, 21.6 g (green 11.8 g, white 9.8 g), one colour change, no supports; hangs 0.2 degrees off
  plumb by the G-code. Nail 68.3 mm below the top, 37 mm in from the left.
