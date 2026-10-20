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
- **Filament:** PLA, AMS slot 3 (see amendments). Bambu Studio slices the pair at 77.5 g; the tests hold
  it under 80 g.

All sizes live in `refill_spool/params.py`.

## Amendments

- **2026-10-20: straps go on with the cap off; the cap gets a lip.** The pre-print review showed that straps
  looped outside both flanges stop the cap turning after ~18°, and the barrel's three strips (slotted full length)
  are only joined at the bottom, so the thread could push them apart and jump.
  - New procedure: unscrew the cap, thread ties down the open slots and round the coil, lift the coil off.
    Tests check the strap paths with the cap off and lift the strapped coil clear at several heights.
  - The cap no longer needs strap openings, so its flange has a solid ring (Ø71 to Ø82) and a lip 2.4 mm tall,
    0.8 mm thick, 0.2 mm outside the barrel, with a 0.6 mm lead-in. Screwed home, it wraps the strips' top ends.
  - The drive notch is on the barrel half only: that side goes toward the AMS lite's drive.
- **2026-10-20: the bore is a tube the full width.** From the user, comparing with the official Bambu reusable
  spool, whose bore runs solid through: the AMS lite hub should bear along the whole spool, not on a 7.2 mm ring at
  one end and a 3 mm ring at the other. The barrel half now has a 1.2 mm tube round the Ø55 bore up to the barrel
  top, and the cap's bore ring lands on its end, so the bore is continuous over the full 65 mm. 71 g sliced (budget
  raised to 75 g; the user's solid printed spools are ~220 g).
- **2026-10-20: PLA, AMS slot 3.** The user has PLA to use up. PLA is stiffer (good for the thin spokes and rim)
  and prints the thread cleaner; it's more brittle if dropped and softens near 55–60 °C, so don't dry filament on
  this spool above ~50 °C. The template's PLA profile slices the pair at 74.6 g (50.7 + 23.9); budget 80 g.
- **2026-10-20: solid floor under the barrel.** From the user: the barrel's strips only met the flange where the
  six spokes crossed them, two small contacts per strip. The barrel half's flange is now solid from the bore out to
  the barrel's outside (Ø55 to Ø80, flange_t thick), open only at the three strap slots. +2.9 g: 77.5 g sliced
  (barrel half 53.6 g, cap 23.9 g).
