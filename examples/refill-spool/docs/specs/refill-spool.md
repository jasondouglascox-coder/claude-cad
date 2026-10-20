# Refill spool

A reusable spool for Bambu Lab 1 kg refill coils that uses as little filament as possible. It only has to keep the
coil on and spin in the AMS lite. Two halves screw together; straps (zip ties) go round the coil so it can come off
the spool in one piece.

- **Flanges:** 6 spokes (6 × 3 mm) and a rim (3 × 3 mm) at Ø200, not solid discs. Picked from three sketched options
  (bare X, 6 spokes + rim, 3 spokes + rim): the rim keeps loops from slipping off the spoke tips and rolls
  smoothly. 3 mm thick, 59 mm between flanges, 65 mm overall (the AMS takes ~67).
- **Bore:** Ø55 for the AMS lite hub, in a 4.5 mm ring 7.2 mm tall on the barrel half (2.5 mm × 3 mm on the cap).
  The barrel half's bore has the AMS lite drive notch at the outer face: 6 mm in, 3 mm into the wall, 3 mm wide.
  Its roof is the part's only bridge (3 × 3 mm).
- **Barrel:** Ø80 outside (the refill's cardboard core is ~Ø82 inside), 1.2 mm wall, all on the barrel half.
- **Thread:** the barrel's top 12 mm is the nut and the cap's spigot is the bolt. Pitch 4 mm, ridges 1.2 mm deep
  with 0.5 mm crests and 40° flanks (they print upright without support), 0.3 mm radial clearance, about 0.43 mm of
  axial play per flank. Ridges run about 1.6 turns engaged. The cap stops when its flange lands on the barrel top.
  Its ridge phase is set so that, screwed home, the cap's spokes line up with the barrel half's spokes, which
  keeps the strap paths clear.
- **Straps:** 3 slots, 10 mm wide, run the barrel's full length midway between spokes. A strap goes under the core
  in a slot, out through both flanges between the spokes, and back over the coil inside the rim (needs the coil
  under Ø190; measure a full one). Tests model each loop at 1.5 mm thick and require it to touch nothing.
- **Filament:** PETG, AMS slot 1. Bambu Studio slices the pair at 56 g (barrel half 35 g, cap 21 g); the tests
  hold it under 60 g.

All sizes live in `refill_spool/params.py`.

## Amendments
