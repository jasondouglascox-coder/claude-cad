# Rose wall decor: design spec (2026-10-22)

References (`docs/references/`, kept local: not ours to publish): the collection mockup (the left, open rose; the user picked it), a photo of a
real rose (the centre: "the center still isn't working for me" until it matched this), and the peony photo for
the next flower. Printer: Bambu A1 + AMS lite, 0.4 nozzle, 0.20 mm Standard. Hung next to the sunflower
(`examples/sunflower-wall`).

## Goal
An open rose, face-on, about 8" (203 mm) across, printed in one go like the sunflower: red PLA, flat back on the
bed, hung on a nail through a hidden keyhole.

## Shape (settled with renders, spikes v2-v6)
- **Outer petals** (24, rose "D"): each petal is its side profile swept around the axis through the angle it
  wraps (an exact curved wall, `T` thick), then trimmed to a pointed outline: the lens where two ellipsoids
  around the petal's foot overlap, so each petal ends in a small point. The side profile rises straight, then
  curves out; the lean grows along the petal to `outer_lean` = 135 degrees at the tip for the outermost petals
  (they roll past level and back down, like an open rose), 45 degrees for the innermost. Petals sit on a golden-
  angle spiral, feet spreading out from the centre; outer petals are longer and wrap less.
- **Centre** (8 petals, "F"): a funnel of small, tightly wrapped petals (each wraps ~220-300 degrees), 0.9 mm gaps,
  nearly upright with a slight outward roll at the rim; their rims step down 8 mm toward the middle, so you look
  down into a vortex of petal edges, darkest in the middle (the real photo). An earlier domed spiral bud read
  wrong: a rose centre goes down, not up.
- **No floor showing, no black.** The user first suggested black in the valleys for depth; a visible floor ring
  read wrong, and once the petals cover the floor (inner petals lean out 45 degrees so their tops cover the gaps)
  black adds nothing. One colour.

## Printing
- Red PLA. The outer petals' curl goes past 45 degrees, so they need supports: tree supports with a PETG
  interface (PETG doesn't stick to PLA, so it peels clean; the user offered it). The centre petals and the inner
  ring lean 45 degrees or less and need none.
- Petal walls `T` = 1.6 mm (four lines). Heights on layers.
- Keyhole in the solid base under the centre, the slot's top at the flower's centre: the nail goes where the
  flower's centre should be.

## Amendments
- 2026-10-22: No lip at the bed (the user, from Bambu: "a rose cut off at that point would not have a lip"). The
  floor was a disc out past the shorter outer petals' feet; now it is a pad under each outer petal, a wedge from
  the centre to the outside of its foot as wide as it wraps (`petals.pad`), so its edge is always inside a petal
  and it still ties every foot into one piece. Tested along 24 directions (`test_no_floor_lip_past_the_petals`).
  A black floor (1.2 mm) was rendered out of curiosity: the petals cover the floor, so it only shows as a glimpse
  deep in the gaps and a thin black line at the base. Not used.
- 2026-10-22: Independent pre-print review (sliced and probed; nothing that would ruin the print). Fixed: tree
  trunks stood on the floor pads between petals red-on-red (tree supports get no PETG bottom interface here), so
  the supports now leave a layer's gap underneath (`support_bottom_z_distance`); and the slicer dropped "small"
  overhang support under the outermost curl tips, leaving one in air (`support_remove_small_overhang` = 0). A test
  holds the prime tower (the template's spot) 3 mm clear of the rose. Accepted as they are: 23 pairs of outer
  petals fuse near their crests (harmless; a few dark lines fill in), and the slicer skips ~0.5 mm slivers at
  the curl edges. Confirmed: no support anywhere in the centre, the keyhole puts the nail on the axis with 1.8 mm
  over its head, the rose hangs within ~7 degrees of its print orientation.
- 2026-10-22: **A 4" rose, four to a plate** (`params.small`, plate `small_roses`; the user: "3 or 4 smaller ones
  vs one large"). The 8" rose stays as it was. Only the plan halves: walls stay 1.6 mm (0.8 would be two lines),
  the centre's 0.9 mm gaps stay (narrower would fuse), and so does the nail. Consequences, found by halving
  straight and looking:
  - The centre has 4 petals, not 8 (8 with full-size walls and gaps need 21 mm of radius: half the small rose).
  - The 11 mm keyhole base is taller than the halved centre petals and capped the funnel flat, and the nail
    head's pocket broke out of its side. The base is 6 mm, with a smaller keyhole: an 8 mm head pocket 2.4 mm
    tall over a 1.2 mm lip, 8 mm slot, a flat 7.6 mm roof (a short bridge) and 2.2 mm over it. Use a small nail:
    head under ~7.5 mm, shank under 4.6 mm.
  - With the base only a few mm under the centre rims it read as a floor; the user: "slightly fill in the middle
    so you don't see the floor". Measured straight on, 78% of the centre was the base's flat top. Now the centre
    petals keep their whole wrap (`centre_backs`: the tip's lens no longer trims their backs off; at 8" it does,
    and 69% of that centre is base, but 3-12 mm down it reads as depth), stand 4-7 mm above the base, lean out
    30-33 degrees together (with the lip, 40-43: still no supports) so you can't see down between them, and wrap
    nearly all the way round; a nub plugs the very middle. 21% shows, as thin dark lines (test: <= 25%). Near
    their rims neighbouring centre petals come within 0.3-0.6 mm and may print fused: one colour, fine.
  - Plate: four in a 2 x 2 square 120 mm apart, the prime tower in the middle (about 9 mm clear of each). They share
    the PETG layers, so four together cost the swaps of one.
  - The small rose's outer petals, with full-size walls, fuse more near their crests and leave a few mm2 nearly
    flat under a curl (off the layer grid); they're out past the feet, on the supports. The tests allow exactly
    that and nothing else.
