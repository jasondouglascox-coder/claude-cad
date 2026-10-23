# Peony wall decor: design spec (2026-10-22)

Reference (`docs/references/`, kept local: not ours to publish): the user's photo of a real peony. A full, tight
bloom: ruffled, layered petals from the outside all the way in, pink fading to near-white at the edges, and a
ring of yellow stamens around a small pink-and-cream centre, only partly visible. Printer: Bambu A1 + AMS lite,
0.4 nozzle, 0.20 mm Standard. Hung with the sunflower (`examples/sunflower-wall`) and the rose
(`examples/rose-wall`).

## Goal
A tight peony, face-on, about 8" (203 mm) across like the rose, soft pink PLA, flat back on the bed, hung on a
nail through a hidden keyhole. The yellow stamens are a separate small print.

## Shape (settled with renders, spikes v1-v8; the user picked "C")
- **Petals are freeform**, not the rose's revolved profiles (a revolve can't ruffle). Each petal is a grid of
  points: columns across the petal, each the petal's side profile (lean growing from `lean0` at the foot to `lean`
  at the tip) swept a little round the axis, ending on a rounded, scalloped rim with a narrow claw at the foot. A
  ruffle pushes the points along the side's normal, `amp * sin(pi * waves * v + phase) * t^2`: flat at the foot,
  full at the rim. Two skins (no OCC offset: it buckled at the corners), ruled edges, sewn into one solid. The
  surface fit uses tol 0.05 and is checked to stay within 2 mm of its points (the default looped 500 mm out).
- **A tight head:** 9 low guard petals around the outside, 70 bowl petals on a golden-angle spiral (feet from 24 to
  62 mm), upright and curling in near the middle, leaning out toward the edge, so ruffled rims run from the outside
  right in to the yellow; and 2 inner petals folding across the opening so only some of the centre shows.
- **One petal rests on the next: no supports** (the user's idea). Under every petal a hidden fill runs down at 45
  degrees onto whatever is below (another petal or the bed): per column, the 45-degree envelope from every point
  above it, under the rim's angle (the petal's wide top, not its narrow claw). From the front you only ever see a
  petal's top face, so the fill never shows. Measured on all 81 petals: overhang past 47 degrees went from 34,556
  to 379 mm2 (0.1% of the surface; the worst petal 21 mm2, at noise level). The guard petals lean at most ~75
  degrees: past that their ruffle crests roll over, and no fill underneath can help a face that faces down on top.

## Centre and hanging
- **Stamens: a yellow insert** (the user chose it over ~120 AMS swaps or an all-pink flower). The yellow sits at
  the same heights as pink petals, so one colour change by height can't do it.
- The insert goes in **from the back**: the folded petals overhang the opening, so it can't pass from the front. It
  is a plug with a 45-degree flared foot, through a matching hole in the flower's centre; the wall behind holds it
  in, the flare stops it going through. Both print without supports (the flare is a 45-degree cone, no bridge).
- The **keyhole** moves off the centre (the insert is there) into a solid boss up the flower's +Y, under the bowl
  petals: the nail goes that far above where the centre will be.

## Colours
- Soft pink PLA for the flower, yellow PLA for the insert. One filament each: the photo's fade to white at the
  petal edges isn't printable in one pink.

## Amendments
- 2026-10-22: **Meshes, not B-rep.** OCC fused the freeform petals into invalid pieces even pairwise (every petal
  was flagged self-intersecting: the fitted skins don't meet their sewn edges exactly), and a fuzzy fuse of all of
  them ran 13 minutes at 6 GB before it was stopped. Each petal is now a mesh straight from its point grids, and the
  flower one manifold3d union (0.8 s), with the hole and keyhole cut after. `cadkit.mesh` carries meshes through
  the checks, renders and plates; no STEP (STL per plate instead).
- 2026-10-22: **No narrow claw.** A petal narrowing to its foot needs fill under its wide top's corners reaching
  past its own outline, and that showed from the front. Petals keep their full width to the foot (hidden down in
  a tight head anyway). Where a petal needs no fill it keeps its exact wall: turning an in-curling tip's wall to
  the rim's angle also showed. Tested: the front view with and without fills differs on under 0.5% of cells.
- 2026-10-22: **Centre, as built.** Three folds (not two), longer (50 mm, from 40) with feet at 25 mm, and 120 stamens: on the
  all-yellow insert two folds left a flat yellow disc in view. About 70% of the yellow shows. The stamens' tilt
  is clipped so they pass through the 20 mm hole; anthers are upright 45-degree cones with domes.
- 2026-10-22: **Keyhole at 70 mm up +Y**, in a slot-shaped boss 3 mm past the keyhole, 10.8 mm tall (1.6 over
  the roof). At 40 mm its entry cut through the thin floor (a hole you could see the wall through), at 55 mm the
  boss showed between the upright inner petals. Tested: nothing shows the wall through the flower; the front view
  is the same without the boss.
- 2026-10-22: Sliced (Bambu Studio): peony 10.9 h, 353 g, no supports generated; stamens 0.8 h, 9 g. The 45-degree
  fill under the low outer ring shows as a thicker band at the bed from a low angle; from the front it's hidden.
