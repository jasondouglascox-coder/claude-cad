# Candle adapter

A black PETG adapter that gets hot-glued into a flat chandelier-style cup (a shallow dish with a ~2 mm lip) and
holds a 20 mm candle.

- Base disc Ø37 × 3 mm sits inside the cup's lip; its top is the floor under the candle.
- Collar: Ø20 hole, 15 mm deep, 3 mm wall (Ø26 outside), 2 mm fillet into the disc, 0.8 mm lead-in chamfer.
- 18 mm tall overall. Prints as it stands: disc on the bed, hole open upward, no supports, no bridges.
- Filament: AMS slot 3 (black).

All sizes live in `candle/params.py`.

## Amendments

- **2026-10-16: flared foot instead of a flat disc.** The user wanted the base as thin as possible and sloping up
  from the ground. The 3 mm disc and 2 mm fillet are gone. The outside is now a revolved profile: 0.8 mm (4 layers)
  at the Ø37 edge, rising on a spline (starting slope 0.45) that turns vertical into the Ø26 collar at 9 mm. The floor
  under the candle is 1.2 mm, so the part is 16.2 mm tall. The flare was picked over a straight cone from rendered
  options. The radius only shrinks going up, so there's still no overhang.
