# Sunflower wall decor: design spec (2026-10-15)

Reference: a real sunflower photo (large dark seed head about 45% of the width, two rings of plain yellow petals
that arch back). Printer: Bambu A1 + AMS lite, 0.4 nozzle, 0.20 mm Standard, PLA.

> **Now (2026-10-21): only the one-piece ~10" print is kept** (`sunflower/flower.py`); the 16" kit below (quarters,
> pins, sockets) was deleted. The sections up to the Amendments describe the original kit and stay as history;
> the amendments of 2026-10-16 and 2026-10-21 describe the print as it is.

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
- AMS: 1 orange, 2 yellow, 3 black, 4 brown (PLA). Orange is the front petals' valley beads (amendment 2026-10-16).

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
- 2026-10-16: A 10" one-piece version (`sunflower/small.py`) for the A1's bed: the same flower scaled across
  (radii and widths only; thicknesses, petal_min and seed size stay), every part stacked in place and printed in
  one go. Front petals are filled down to the bed (they'd otherwise start over the arching back petals). The seed
  head sits on a hidden yellow riser just above the tallest yellow, so the black never shares a layer with
  yellow; the riser flares out from the hub at 45 degrees (the head is wider than the hub). No pins: one keyhole
  behind the first front petal's root, placed from `docs/measurements.md` so the flower hangs centered in its
  20 3/8" gap (nail 8" down: 2 3/16" above the flower's center), with a 45-degree roof ending in a 0.7 mm bridge.
  The round 250 mm flower leaves Bambu's prime tower only the bed's front-left corner (30 mm wide); with it there
  the plate slices in 9.1 h, ~201 g (before the beads below).
- 2026-10-16: Orange beads down the front petals' middle five valleys (both sizes), for depth from a few feet
  (the user's idea: blend the only two warm colors there are). Each bead is the top 0.4 mm of the petal along
  its valley, flush with the surface, starting at the top of the arch (r 98 mm on the 16") and running to r 130:
  it widens from one line to 1.2 mm over its first 6 mm, then tapers back to one line. Mocked up first on one
  petal against a thin single line in the middle five valleys and wide beads in all nine; Bambu put them at
  11 / 21 / 14 layers shared with yellow. Chose the middle five, wide and tapered (14 layers, about +21 min and
  +3.3 g per front plate), with the fade-in added so a bead doesn't start with a hard edge. Starting at the
  arch's top instead of the head's edge keeps the swaps down. **This breaks "one color change per plate" on
  purpose**: the AMS swaps on each layer the beads cross. Bead lengths scale on the 10"; widths don't (the
  nozzle sets them). Sliced: a 16" front plate is 2.75 h, 59.4 g (orange on layers 29-42); the 10" is 9.2 h,
  203 g (orange on layers 59-72, then black and brown), 16 swaps in all. The user liked the render: "it adds
  the depth we were missing".
- **2026-10-16, color budget per plate.** cadkit now warns when a plate swaps colors more than the user's budget
  (`CADKIT_COLOR_CHANGES`, default 1). The bead swaps above are accepted, so `front_quarter` and `sunflower_10in`
  carry `Plate(color_changes=...)` set to what their beads cost (cadkit counts 16 and 18; Bambu sliced the 10" at
  16). The other plates stay held to the budget. The 10" flower centers on the bed's middle, rectangular beds
  included; its slicer tests skip on setups with fewer than 4 colors.
- **MakerWorld (2026-10-16):** one model with two print profiles, each a sliced project with every plate
  (`build makerworld`): `sunflower_16in` (back quarter, front quarter, seed head; "(print 4)" where it applies) and
  `sunflower_10in`. They can't share a file, because the 10" keeps its prime tower in the front-left corner. The
  16" plates now pack around the A1's back-left prime-tower corner (cadkit); the plate list didn't change.
- 2026-10-21: The user moved to printing the 10" only, and asked for two changes after looking at it in Bambu.
  **Front petals thinner, sweeping back to the plate:** they had been filled to the bed under the 16" shape, so
  they stood as 15 mm slabs with walls. Now each front petal is solid from the bed with its own heights: level at
  `front_top` = 12 mm under the head out to its rim, then falling to the tip at the plate; across, the edges come
  down to the back petals' midribs (`Ring.edge`), so they read as thin petals lying on the back ring. **The seed
  head down onto the petals:** there was a gap because the head stood on a riser above the old 15 mm petals. Now
  the riser stops at `front_top`, where the petals meet the head's rim, so the black still never shares a layer
  with yellow. A rounded black shoulder sweeping up from the petals was tried and dropped ("not the connection");
  instead the black is a 1 mm floor out to the rim (`center_t`) and the seeds run out to the rim (`seed_edge`
  0.6) and dome 9 mm up to the middle (`seed_dome`): the head rises straight from the petals. Still one seam to
  black and one to brown; more brown to print. The user liked it ("that looks better").
  The riser now fills all of the head's underside (it flares from the hub on the bed, then stands at the rim's
  width), since the petals' sides slope away under the head. Sliced: 9.4 h, 177 g (124 yellow, 3 orange, 14
  black, 37 brown); the beads share layers 38-57 with yellow, so 20 swaps there plus the two seams.
- 2026-10-21: **The 16" kit is deleted** (user: print the 10" only): quarters, seams, pins and sockets, plates,
  the assembly clash test, the 16" builds, tests, images and README section. What the 10" needs stays: the
  petals (`parts/petals.py`, from the quarter code), the seed head without sockets, the seed layout. The design
  is still drawn at 400 mm in `params.py` and scaled to the bed by `flower.params()` (radii and widths only).
  `small.py` became `flower.py`. The beads are now cut from one front petal before the ring is fused, instead of
  from the whole fused flower (that boolean made the tests take an hour).
- 2026-10-21: Some variety in the beads (the user, from Bambu's preview: "middle slightly longer than the
  outsides"). They all still start at the top of the arch; the middle bead runs to `bead_r`'s end and each step
  out toward the edges ends sooner, the outermost pair `bead_falloff` = 25% of the length short
  (`layout.bead_end`). Each keeps its fade-in and taper to one line. Sliced: 9.3 h, 176 g; the beads now share layers
  42-57 with yellow (16 swaps, was 20), 18 in all.
