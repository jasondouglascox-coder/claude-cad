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
- **Six bells** hanging below it, side-on: each lies in the wall's plane, its apex at the pedicel and its mouth
  down. Along the axis: a rounded shoulder, straight-ish sides widening a little, a slight waist, a flared rim.
  The rim is scalloped into six lobes: the two at the sides curl back in the wall's plane (horns); the two facing
  you reach past the rim, so the bell's lower edge is scalloped from the front. A shallow cone hollows the mouth.
  Bells are 12 mm radius at size 1, 24 mm long, 0.85 as deep as wide; sizes 0.8 to 1.0, smallest at the tip.
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
The keyhole hides under the third bell, the one over the centre of mass: the nail rests 8 mm down its axis from
the apex, moved sideways to straight above the centre of mass, so the sprig hangs within a degree of plumb. A
6 mm slot, a 9.5 mm head, a 44-degree roof with 1.2 mm of wall all round. Nail: 70 mm below the sprig's top, 40 mm
in from its left edge.

## Build
Meshes from the start (peony lesson: B-rep booleans give up on freeform bodies), one `cadkit.mesh` union, the
keyhole cut, slivers collapsed (`Mesh.simplify`), then cut at the seam into green and white bodies. No STEP; the
plate comes with an STL.

## Amendments
- 2026-10-26: Sliced (Bambu Studio): 1 h 08 m, 22.1 g (green 11.4 g, white 10.8 g), one colour change at layer
  25, no supports generated.
