# Sheep antlers: spec

Reindeer antlers for a small black sheep-head figure, held by its slot. A Santa hat may follow on the same nub.

## Fit

- The slot in the back of the head (see `docs/measurements.md`): an arc 30 mm across, 5 mm tall at the center,
  its top 3 mm under the top of the head, at least 5 mm deep.
- Not the whole slot: one nub at the center, 5 mm along the slot, 4.8 mm tall (0.1 under the slot each side), 5 mm
  long, 0.6 mm lead-in chamfer on the tip. The user's call: "make a nub that shoves in". Only 5 mm of the arc, so
  its curve doesn't matter.
- The plate's bottom edge is the slot's bottom, so nothing hangs down onto the body behind the head.

## Shape

- A flat 4 mm plate behind the head: a band ±16 mm wide following the head's top arc (guessed at R 30 from the
  slot's chord) and 5 mm above it, so it shows like a headband (see amendments: now hidden).
- Two mirrored antlers from the band: a beam curving up and out to 82 mm tip to tip (the sheep is just shy of 88 mm
  across the ears), a tall inner tine 45 mm over the head, an outer tine, a short brow tine. Strokes taper
  5.5 → 3.2 mm (beam) and 4.5 → 3.2 mm (tines), round tips, 1.5 mm rounds where they join.

## Print

- Lies on its back, nub up. Brown PETG (AMS slot 2), one plate, no supports, no color changes.

## Amendments

- 2026-11-27: the first print's nub (4.8 mm) was too loose. Fit tabs added: five 12 × 12 × 2 mm handles with nubs
  5.0 / 5.2 / 5.4 / 5.6 / 5.8 mm tall (1–5 notches on top), their own plate. Put the winner in `nub_h`.
- 2026-11-27: the band showed as thick brown over the head (13 mm on the center line). Now 8 mm (`band_h`), level
  with the head top, so it hides behind the head and only the antlers show.
- 2026-11-27: fit tab 3 (5.4 mm) holds: `nub_h` 4.8 -> 5.4, 0.4 over the measured 5 mm slot. Centered on the slot it reaches 0.2 under the slot bottom, so the plate's bottom edge drops 0.2 to meet it (`Params.bottom`).
