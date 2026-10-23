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
- **Filament:** PLA, AMS slot 3 (see amendments). Bambu Studio slices the pair at 89.3 g; the tests hold
  it under 95 g.

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
- **2026-10-20: strap tracks instead of slots; solid cap hub.** From the user:
  - A tie pushed down a through-slot could wander into the barrel and miss the opening at the bottom. Each strap
    now has a track: a 7 mm groove in the barrel's outside, 0.4 mm deep, leaving 0.8 mm of wall behind it. With
    the core over it, the track is a closed tunnel 1.4 mm deep from the barrel top out through the flange, so it
    takes zip ties up to ~6 × 1.2 mm. The barrel is one tube again and the nut thread runs unbroken. The cap lip
    stays (it keeps the 1.2 mm barrel from spreading and centers the cap).
  - The cap's bore ring met the rest of the cap only at the spokes, like the barrel did. The cap's flange is now
    solid from the bore out to the lip.
  - 81.7 g sliced (barrel half 55.9 g, cap 25.8 g); budget 85 g.
- **2026-10-20: the 6 × 3 × 3 mm feature is a core key, not a bore notch.** From the user: it goes on the
  filament side of the barrel and sticks into the refill's cardboard core, so the coil turns with the spool. It's
  now a key on the barrel's outside at the barrel half's flange, 6 mm up the barrel, 3 mm out (to Ø86, inside the
  core's ~Ø87 outside), 3 mm wide, standing on a spoke. The notch in the bore is gone, and with it the 4.5 mm × 7.2
  mm bore ring that held it: the bore is the plain 1.2 mm tube. The barrel half now has no bridges at all. The coil
  model carries a notch 0.5 mm round the key (unmeasured). 80.4 g sliced (barrel half 54.7 g, cap 25.8 g).
- **2026-10-20: sized to a measured refill; no cap lip.** The user measured a real refill: core 82 mm inside,
  filament 6.75" (171.5 mm) outside, coil 61 mm wide. The coil was 2 mm wider than the space.
  - 62 mm between flanges (0.5 mm a side) and 2.8 mm flanges: 67.6 mm overall, inside the AMS lite's 68 mm
    (Bambu store: 40–68 mm wide, 53–58 mm bore).
  - The cap lip came out: its outside sat at Ø82, exactly the core's inside, so the core would rub on it as the cap
    screwed down. It was there to hold the old slotted barrel's strips; since the strap tracks, the barrel is a
    whole tube. The cap's flange stays solid from the bore out over the barrel's top end.
  - Straps pass over the coil at Ø171.5, well inside the rim.
  - 79.8 g sliced (barrel half 55.7 g, cap 24.0 g).
- **2026-10-21: smaller key.** From the user: the core key is 2 mm wide, 3 mm out from the barrel and 3 mm along
  it from the flange (was 3 wide, 3 out, 6 along). 79.7 g sliced.
- **2026-10-21: 67 mm overall, 3 mm flanges, 61 mm inside.** The user's enclosure takes 67 mm at most, and the
  cardboard core measures 60 mm at its middle. 61 mm between flanges (0.5 mm a side) and 3 mm flanges make 67 mm.
  4 mm flanges (57 mm inside) can't hold a 60 mm core; 2 mm would fit but each spoke would be about a third as stiff
  (bending stiffness goes with thickness cubed), so 3 mm it is, in PLA (stiffer than PETG). 80.5 g sliced.
- **2026-10-21: a middle ring on both flanges.** Ø130, 3 × 3 mm, across all six spokes: the flanges flex less and
  the open gaps loose turns could slip through are halved. On the barrel half it has a 10 mm gap at each strap,
  because a tie crosses that flange's outer face from its track to past the coil: a whole ring would trap the loop
  and the coil couldn't lift off (the lift-off test caught it). The cap's ring is whole (straps go on cap off).
  The user accepted the extra plastic: 87.3 g sliced (barrel half 59.0 g, cap 28.3 g); budget 95 g.
- **2026-10-21: the middle ring is whole on both flanges.** From the user: the gap ends on the barrel half would
  snag filament; they'll move each tie round the ring when lifting a strapped coil off. The lift-off test now
  checks the coil alone. 87.6 g sliced.
- **2026-10-23: barrel Ø82, snug in the core.** From the user's first print: the Ø80 barrel was loose in the core
  (a 1.75 mm filament slid in beside it). The barrel is now Ø82 with a 2.2 mm wall, grown outward, so the thread
  inside and the strap tracks' floor (and their 1.4 mm tunnel) stay where they were. The 3 mm key stays (the user:
  it works); on the bigger barrel its tip is at Ø88, past the forum's unmeasured Ø87 for the core's outside, so that
  check is gone. 105.6 g sliced (barrel half 76.9 g, cap 28.8 g); budget 115 g.
- **2026-10-23: back to a Ø80 barrel, with ribs to Ø82.** The user measured the core again: 82 inside, 87 outside
  (the forum figure was right). The solid Ø82 barrel cost 18 g, and its 3 mm key would have reached Ø88, past the
  cardboard into the filament. Now the barrel is Ø80 × 1.2 mm again, with 12 ribs 2 mm wide out to Ø82 (snug in the
  core), round on the outside with a 1 mm lead-in chamfer at the top, midway between the key and the strap tracks.
  The 3 mm key on the Ø80 barrel ends at Ø86, inside the cardboard. The thread printed and screws together
  perfectly (user). 89.3 g sliced (barrel half 61.0 g, cap 28.3 g); budget 95 g.
