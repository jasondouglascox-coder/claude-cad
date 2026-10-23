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
    head 7 mm or less (the head hole slices to ~7.7 mm), shank under 4.6 mm.
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
- 2026-10-22: Independent pre-print review of the small roses (G-code of all four parsed, arcs included, and
  compared layer by layer with the model). Fixed: tree supports (Bambu's tree(auto) goes "hybrid" under the flat
  roof) stood on the bed, came up through the head hole and filled the nail's pocket, PETG-capped, 6.8 mm wide
  behind a 4.6 mm slot: trapped, and 4 of the 24 swaps. `bridge_no_support` changed nothing; a support blocker
  over each keyhole does (`flower.blocker`, through cadkit's `Plate(blockers=...)`); a slow test scans the G-code
  for support inside any keyhole. A blocker must take in the whole overhang: Bambu grows support back from any
  strip left outside it. The 8" rose (45-degree roof, no support there) gets one too. Head hole: 7 mm heads.
  Accepted: ~25 patches of 0.3-8 mm2 at the fused crests (z 12-13.2, r 30-42) print over air facing down under
  the curls: a rougher hidden underside. Fine: every curl tip supported; nothing supported in the centre;
  supports start on the bed and keep 0.11 mm off the petals; ~10 mm between roses, 5.4 mm to the tower.
- 2026-10-23: The user opened small_roses.3mf in Bambu Studio: "supports are not set". The window loads the
  project's presets and applies only the settings named in `different_settings_to_system`, which cadkit didn't
  write, so every support override (and the tower's spot) opened as the stock 0.20 mm Standard preset has it. The
  command-line slicer reads the whole file, so the slicer tests sliced with supports and missed it. cadkit now
  writes the list; a test holds the support settings on it.
- 2026-10-23: **Small rose: supports only on the outside** (the user: "can all inside petals just end at 45 deg so
  only supports are on the outside?"). Measured first: of the 23 curls, 1-15 hang wholly over other petals, 16-18
  nearly so, and only the outer five (19-23) mostly over bare bed. Spiked both ways and sliced one rose each:
  - A, petals 1-18 lean only to 45 degrees: the inner petals stand up as a cup with a few flared outer ones, a
    different rose; and 45 is on the limit, so the slicer still supported some 30-40 mm out. 60.5 g + 4.2 g PETG,
    2.64 h.
  - B, chosen: petals 1-18 keep their curl and rest on a hidden fill (`params.filled` = 18, `petals.profile`):
    everything under the curl above a 45-degree line from the tip down-in to the petal's own stem, or to the bed
    just outside its foot. Straight on the curls cover their fills (height maps: ~1.2% of the rose reads higher,
    thin lines where a fill raises the bottom of a gap by ~1 mm; test: <= 2%). The rose is heavier (55.8 cm3, was
    37.6) but takes less filament: 52.7 g + 3.2 g PETG, 2.69 h, 18 swaps a rose (was 61.5 g + 4.7 g, 3.11 h, 22).
    Every support now stands on the bed outside the petals' feet (nearest 39.6 mm from the centre, feet end at
    37.7; a slow test holds it), so cleanup is round the rim, none in the tight gaps.
  The 8" rose is unchanged (`filled` = 0).
- 2026-10-23: Pre-print review of the fills (G-code of all four roses rasterised per layer against the mesh):
  nothing prints over air but the keyhole's bridge, every PETG contact is under petals 19-23, no support touches
  a fill, supports start only on the bed, slivers and narrow gaps fewer than before. One visible flaw, fixed: the
  fills of petals 14-18 reached the bed outside their feet and poked out through the outer petals' stems, a
  45-degree skirt (median ~4 mm, up to 6.5 mm out at z 5-11, in ~85% of directions), dark under the outer curls
  seen from ~12 degrees off the wall. Each fill is now cut back to inside the unfilled petals (`petals.shadow`:
  everything out from a petal's stem and under its curl); measured the same way, nothing reaches past the
  unfilled rose (<= 0.1 mm; test <= 0.3). Where curls 14-18 reach past an outer petal they overhang again, over
  bare bed: supports stand there, and per direction every support move is still past that direction's feet (a
  slow test now checks per direction, not against the outermost foot). One rose: 54.1 g + 3.8 g PETG, 2.8 h, 18
  swaps (unclipped 52.7 g + 3.2 g, 2.69 h). Also from the review, accepted: two sealed air pockets in the base
  (43 and 26 mm3, harmless); supports passing 0.15-0.2 mm from the fills now have more room.
