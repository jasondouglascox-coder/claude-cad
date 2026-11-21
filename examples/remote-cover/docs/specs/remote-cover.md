# HEXBUG remote battery cover: spec

## Problem

The remote's battery cover and its screw are lost. The pocket is keyhole-shaped: a rectangle with a round-ended ear
on top over a brass threaded insert, which sits in a circular indent about 5 mm across. Two slots under the pocket's
bottom edge take the cover's tabs.

## Design

- The original's outline (measurements.md), 0.05 mm in on every edge for printed growth, 1.6 mm thick.
- Two tabs 2 × 1 mm, 0.8 mm thick (0.75 on layers), flush with the inside face, 6 mm in from each side.
- No screw: a 0.8 mm plug under the ear, concentric with the screw hole, presses into the indent; a 0.2 mm chamfer
  leads it in. A 1.6 mm hole through ear and plug keeps the screw option (M1.4).
- Prints outside face down, plug up. The only overhangs are the tabs' undersides (1 mm out, at Z 0.8), accepted:
  they hide in the slots and a little droop doesn't matter.
- The plug size isn't known, so one plate carries a ladder of five covers, plugs 4.8 to 5.2 mm, the size engraved
  0.2 mm deep on the inside face.
- Gray PETG, AMS slot 1.

## Amendments

### 2026-11-21: fill the pocket, not the old cover's outline

The first print (the old cover's 25 x 15 outline) sat loose: the "good" cover is from another remote. Measured off
photos against the printed cover (known size): the pocket is 26.1 x 16.2 with 1 mm corners, its ear recess 6.2 wide
reaching 6.9 above the top edge, the insert 2.6 above the top edge, centered. The tab slots are 11.6 apart and off
center: 4.8 and 6.8 from the middle (left and right, seen from outside); the user saw the tabs needed spacing apart.

- The cover is the pocket's outline less a clearance on every side; the plate prints 0.1, 0.2 and 0.3 (engraved
  "1", "2", "3" inside) instead of the plug ladder.
- The plug is now a locator, 4.6 against the ~5 mm indent, so a photo error in where the indent is doesn't stop the
  cover seating; the snug outline holds it in.
- The hole sits over the insert, no longer at the ear's round end.
