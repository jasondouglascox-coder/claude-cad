# Circle jig

Asked for (2026-10-29): mark a 17" circle and split it into four exact quarters. A jig screwed to the centre with a
pencil at the end, pencil spots every inch for options; at the base a cross with ~2" arms for laying out the
quarter lines, "or slightly offset so I can use it as a straight edge".

## Decisions

- **Pinwheel, not a cross.** Each arm is a strip on one side of a line through the pivot, so every arm has a
  straight edge exactly on a radius: the bar draws the radius directly, and a quarter turn puts the next arm's edge
  on that line and the bar on the next quarter. No slits, no extending short marks.
- **Holes every inch of diameter** (½" of radius), 4" to 17", numbered by diameter. Each sits `hole_off` in from
  the bar's straight edge, at `sqrt(r² - hole_off²)` along it, so it is exactly r from the pivot.
- **Pencil holes:** a 2 mm throat at the bottom for the point, a 30-degree cone above guiding the pencil to it.
- **Short arms' straight edge 2"** past the 26 mm hub (`arm_edge`). Alignment error over 2" is about 0.3°, about
  1 mm at an 8.5" radius; the fourth turn landing back on the first line checks it.
- **Bevel** 3 mm at 45° on top of each straight edge, leaving a 3 mm vertical lip at the bottom for the pencil.
- **Printed across the bed diagonal:** pivot to bar end is ~226 mm and the arms reach back 77 mm; one piece fits.
- One colour, orange PLA (slot 1), 6 mm thick, raised 0.6 mm numbers. Pivot 4.5 mm for a #8 screw.

## Amendments

- 2026-10-29: placed at the turn that leaves the most room (41.5°, from `bed_angle`) and centred on the whole bed:
  at 45° in the usable square it cleared one edge by 0.2 mm. Now 8 mm on every side, still one piece.
- 2026-10-29: **17" is the radius, not the diameter** (the user's correction): a 34" circle. Holes every inch of
  radius, 2" to 17", numbered by radius. The bar is now 442 mm from the pivot, so it prints in two: the hub piece
  (arms and bar past the 8" hole, usable alone) across the diagonal, and a straight extension along X. They butt
  midway between the 8 and 9 holes, clear of both, locked by the railroad's bow-tie key (12 × 14 × 8 mm waist) flush
  through the bar at zero clearance (`fit_key`, from the railroad's fit test), and are glued with CA against a
  straightedge so the edge can't kink at the seam. A spare key prints with the extension.
