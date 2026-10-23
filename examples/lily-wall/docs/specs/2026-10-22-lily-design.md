# Lily wall decor: design spec (2026-10-22)

Reference (`docs/references/`, kept local: not ours to publish): the user's photo of a lily. Six pointed, recurved
tepals, each with a deep purple heart fading softly into white tips and white margins; a white-green throat; long
pale stamens with dark anthers, a pistil. Printer: Bambu A1 + AMS lite, 0.4 nozzle, 0.20 mm Standard. Hung with
the sunflower, the rose and the peony.

## Goal
An open lily, face-on, about 70% of the bed across (~180 mm), printed in one go flat-back on the bed: white and
purple PLA blended smoothly, hung on a nail through a hidden keyhole.

## Colour: by height, faded by layers (settled with renders; the user picked the long fade)
- Printed face-up, each tepal rises straight out of the throat, is level 40% along, and recurves down until its
  tip lands on the bed; its edges curl down from the midrib. So the purple heart is the highest part of each
  tepal, and the tips, margins and throat are low: white below a height, purple above it gives the photo's
  pattern, the seam following each tepal's shape. The seam sits at 66% of the tepals' height (purple from ~18% to
  ~75% along).
- **The long fade:** in an 8 mm band round the seam, whole layers alternate white and purple, the purple share
  rising from 0 to 1 (error-diffused, 40 layers of 0.2 mm). Every switch is a whole layer: one AMS swap each, about
  21 in all. Up close it's fine stripes following the curve; from a step back it reads as a fade.
- The anthers stand above the band: purple, like the photo's dark anthers.

## Printing
- **Tree supports** (the user: solid fill under the petals "would look wrong"; the arch is flatter than 45
  degrees, so corbelling from its legs can't reach its top). First planned with a PETG interface; see Amendments.
- Filaments: 1 white PLA, 2 purple PLA (3 and 4 unused).
- Tepal walls 1.6 mm. The lily is one mesh (petals unioned with `cadkit.mesh`); its white and purple bodies are the
  mesh cut into layer slabs, parts of one object.
- Keyhole in a solid boss under the throat: the nail goes where the centre will be.

## Amendments
- 2026-10-22: **Supports in the same PLA, not a PETG interface** (the user, from the numbers). Sliced, the gray PETG
  interface swapped 110 times (the arches touch supports over many layers): 9.8 h, 159 g, mostly purge. With the
  trees and their interface in whatever's loaded, a layer's gap above and below: 4.3 h, 50 g, and exactly the fade's
  21 changes (tested through Bambu Studio). Support marks land on the undersides, which face the wall.
- 2026-10-22: As built: tips land on the bed at lean 145 / 144.5 degrees (144 / 142 on the spike, integrated more
  finely); one tepal points straight up; the throat's floor is a white cone 34 mm across at the bed (it holds the
  keyhole, a 10 mm one: the throat is small), with the stamens' feet 1 mm up inside it.
