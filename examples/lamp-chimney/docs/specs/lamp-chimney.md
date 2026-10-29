# Lamp chimney

A printed white replacement for the broken glass chimney of a small LED oil-lamp-style lamp. It stands in the
scalloped gallery on top of the lamp, where three spring tabs grip its foot, and glows from the LED candle inside.

- Foot Ø40.0 outside (the old glass's outside diameter), 10 mm into the gallery, 1.2 mm wall (three lines) so the
  tabs can squeeze it; its top steps in to the thin wall on a 45-degree chamfer inside (faces up, no overhang).
- Body Ø40 straight for 31 mm above the foot, round the LED candle.
- Shoulder at 45 degrees from vertical down to the Ø26 neck, both bends rounded (R8 outside) so it reads smooth.
- Neck Ø26 to the top; 131 mm tall overall, open at both ends.
- Wall one line thick (0.42 mm) everywhere above the foot, as thin as the 0.4 nozzle prints, so it glows evenly.
  If one line fails to print, `wall = 0.84` (two lines) is the fallback.
- Prints upright in the middle of the bed (in a corner the slicer clips the outer brim), no supports. White PLA, AMS slot 1. Slicer settings in the project: Arachne walls (one bead in the
  thin wall, three in the foot) and an 8 mm brim outside and inside the foot (`outer_and_inner`).

Sizes other than the foot are read off the product photo against the 40 mm foot (neck ≈ 0.65 of the foot, glass
≈ 3.3 foot widths tall). All sizes live in `lamp_chimney/params.py`.

## Amendments

- **2026-10-29: spiral (vase) mode, no seam.** The user asked for no seam, and Bambu Studio warned of "floating
  regions" on the one-line wall printed layer by layer (a false alarm: every layer was one closed loop; a 30-degree
  shoulder warned too, two lines didn't). The project now sets `spiral_mode` with the foot's 50 layers as bottom
  shell: the foot prints as solid 1.2 mm rings, then one bead climbs the outside continuously to the top. Arachne and
  `wall_loops` are no longer set. Slices with no warning, 59 min. Also one wall loop, no top shell and 0% sparse infill:
  the rest of what Studio's GUI requires with spiral mode (it asked to change them on opening); the foot stays solid,
  being all bottom shell. Fallback if the spiral fails: turn spiral off and
  set `wall = 0.84`.
