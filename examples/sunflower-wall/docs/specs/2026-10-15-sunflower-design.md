# Sunflower wall decor: design spec (2026-10-15)

Reference: a real sunflower photo (large dark seed head about 45% of the width, two rings of plain yellow petals
that arch back). Printer: Bambu A1 + AMS lite, 0.4 nozzle, 0.20 mm Standard, PLA.

## Goal
A 400 mm (~16") wall sunflower that prints without supports, assembles without glue, and shows no seams.

## Pieces (9 prints, 12 pins)
- **Back petal ring**, 4 identical quarters (yellow). 16 petals; each quarter owns 4 petals and a 90° wedge of a
  hub disk (`hub_r`, `back_t` thick) that sits under everything.
- **Front petal ring**, 4 identical quarters (yellow). 16 petals centered over the back ring's gaps; hub wedge
  `front_t` thick, sitting on the back hub.
- **Seed head**, one piece (black + brown, one color change): a disk 180 mm across with a 45° bevel underneath,
  black up to `center_t`, then brown diamond seeds (Voronoi cells of Vogel's Fibonacci spiral, pyramid tops), with wider black
  gaps in the middle (dark eye) and at the rim (darker ring).
- **Snap pins** x8 + 4 spare (yellow), printed flat so the barbs flex along the layers.

## Hiding the seams
- Back quarter boundaries run through back-petal gaps; a front petal sits over each one.
- Front quarter boundaries run through front-petal gaps (open air between petals), offset from the back
  boundaries by about 45° (the nearest front gap), so quarters overlap like brickwork.
- Both hubs, where the quarters actually meet, are under the seed head.

## Arching petals
Printed flat (flat back on the bed). The top surface is a loft of cross sections: high along the midrib, lower
at the edges, and along the length it rises out from under the seed head's bevel, peaks, and falls toward the tip
(`profile` per ring). Back petals stay under the front ring's flat underside; front petals stay under the seed
head and its bevel.

## Joining
Each pin goes in from the back: head in a recess in the back hub's underside (flush with the wall), shank through
a back quarter and a front quarter, barbs snapping over a throat inside a socket in the seed head. Pins sit
midway between neighbouring back and front boundaries, so every quarter is held by two pins and every pin
ties a back quarter, a front quarter and the seed head together. Slot clearance `fit` (tune with
`examples/fit-coupon`).

## Hanging
A keyhole in each back quarter's hub (any quarter can be the top one): the screw head drops through a round entry
at the bottom 1.6 mm lip and slides up a slot, held under the lip, with the front hub closing the pocket above.

## Printing
- Every face that faces down is a pin-head ledge (about 1 mm) or a socket roof under 3 mm²; no supports.
- Tops and color seams on 0.2 mm layers; petal plates are one color, the seed head has one change.
- AMS: 1 orange, 2 yellow, 3 black, 4 brown (PLA). Orange is spare (try it on the back ring for depth).

## Amendments
- 2026-10-15: First concept (seams following petal edges through a split seed head, 4 colors stacked by height,
  orange flames) replaced after the user asked for a one-piece clip-in center, arching petals, and up to 9
  prints, and sent a real sunflower photo: big dark center, plain yellow petals.
- 2026-10-15: Pre-print review fixes. Pin arms bent 4% squeezing through the slots (PLA cracks around 3-4%): split
  lengthened 7 → 10 mm with a half-round end, now 1.5% (`layout.pin_strain`, tested < 2%). Barb play over the
  throat 0.1 → 0.3 mm (`pin_play`), since three stacked prints add up. Three pins per back plate: 12, so 4 spare.
  Eye seeds 1.8 → 2.2 mm so their tops print, and Vogel spacing 2.45 → 2.55 so seeds keep a one-line gap
  (1,177 seeds).
- 2026-10-15: Seeds are diamonds, not round cones (user's photo of a real seed head). Each seed is its Voronoi cell
  in the Vogel spiral (neighbours along the spirals meet in diamonds), shrunk by half the black gap, narrowed to
  80% across the radius, and lofted to a pyramid with a flat top 35% of the base. Gaps: 1.4 mm in the eye,
  0.5 mm in the body, 0.9 mm at the rim. Rim slivers whose tops wouldn't print are dropped (1142 seeds).
  Orange accents were tried (bands at the base, orange tops, feathered bands) and parked: base bands don't
  show, the others didn't look right.
- 2026-10-15: From the user's Onshape look and a photo of a real head. The middle had lost its seeds (a filter
  dropped small seeds whose tops looked too small); small seeds now get a bigger flat top instead, and a test
  requires a seed near every spot of the head. The head domes: each seed is a column from the flat black floor
  (the color seam stays one flat layer) up to a shoulder that is `seed_dome` = 7 mm higher in the middle than at the
  rim, then its pyramid. Petals get 9 lengthwise vein grooves 0.4 mm deep that follow the petal's width, so
  they gather at the root and tip. Cross sections are now straight-segment polygons: a spline through them
  smoothed the grooves away.
