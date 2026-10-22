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
- **Centre** (7 petals, "F"): a funnel of small, tightly wrapped petals (each wraps ~300 degrees) with ~1 mm gaps,
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
