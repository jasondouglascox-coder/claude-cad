# Mini sunflower: design spec (2026-10-30)

Reference: the user's photo of a sunflower (`docs/references/photo.webp`, local only): about 22 plain yellow
pointed petals, a brown head about 44% of the width, a black eye in its middle about a third of the head across.
The user asked for small sunflowers, smaller than the 4" roses: a black dead centre sunk in some, a wider brown
centre sticking up some, yellow petals; the 10" sunflower as a loose reference, no real seeds but some texture.
Printer: Bambu A1 + AMS lite, 0.4 nozzle, 0.20 mm layers, PLA.

## Shape
- 3" (76.2 mm) tip to tip. Two rings of 12 pointed petals, the front ring over the back ring's gaps, each solid
  down to the bed: the back ring lies flat (1.6 mm at the midrib, 0.8 at the tip); the front ring rises to 4 mm
  under the head's rim and sweeps down to 1.2 mm at its tip, its edges kept above the back petals. Three
  one-layer vein grooves along each petal. No two petals the same size (up to 6% shorter, 8% narrower, by the
  golden angle's walk): it looks less stamped, and neighbours that were mirror images met edge to edge, which
  left the mesh unsound.
- The head (33 mm across): a hidden yellow riser to 4 mm, a two-layer black disk, and the brown ring on that,
  from the eye's edge (r 5) to the rim (r 16.5). The ring's inner wall drops 1 mm straight to the black, which is
  left open: the eye sunk about 4 mm below the ring's top. It peaks 3.4 mm over the black (4 with the texture), then rounds down to
  a 0.4 mm edge at the rim.
- Texture, picked from three spikes (smooth, spiral diamonds, seed bumps): **spiral diamonds**, the product of two
  crossing spiral families (21 and 34) through Vogel's seed spiral, 0.6 mm tall, fading out near the ring's edges.

## Printing and hanging
- No supports: everything is a heightfield over the bed but the keyhole, whose 8 mm flat roof is the one bridge.
- Colours by height: yellow, black, brown; 2 swaps a plate (`Plate color_changes` 2 over the budget of 1,
  accepted with the design).
- Keyhole under the head: the nail rests 6 mm above the centre; entry 8 mm, shank slot 4.6, lip 1.2, 2 mm head
  room. That's why the black starts at 4 mm and not the spike's 2.6: at least 0.6 mm (here 1.2) over the roof.
  The printed centre of mass is within 0.2 degrees of plumb under the nail.
- Plate: four in a square 96 mm apart, the 30 mm prime tower in the middle. Bambu: 2 h 9 min, 34.4 g.

## Amendments
