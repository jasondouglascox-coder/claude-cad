# Lessons learned

From building `examples/near-ceiling-track`: a 3D-printed HO railroad shelf around a whole room, 15 part types and
~220 tests. Each lesson is a thing that went wrong (or nearly did) and the rule it became.

## Measuring the real world

- **Check that measurements close.** Walls: the long wall should equal the opposite wall plus the alcove, the front
  should equal the back plus the alcove. The first set was off by 1/8" one way (tape tolerance) and 3/8" the other.
  The right move was to say which reading to retake; when the user had already read it three times, the answer was
  "the room isn't square", not "measure again".
- **Model square, absorb the error where parts are cut to fit anyway.** The corners were identical printed units;
  the straight runs are made of bays set from real stud positions, so a 3/8" short wall just means slightly shorter
  bays. Keep the measured values next to the model's (`Room.misfit()`), and have the build print a note.
- **Record where each measurement was taken from.** "From the back wall" vs "from the front" mattered for every stud.
  Users also flip left and right depending on where they stand: map by geometry (the long wall, the alcove), not by
  their words.

## Geometry

- **Generate sequences by construction.** The room loop was rebuilt as "each corner, then a run to the next corner's
  entry", so the loop closes by construction; a test still checks the last section meets the first.
- **Model the environment as solids, even what you don't draw.** The front wall stayed out of the render, but a solid
  front wall in the clash test proved no bracket or anchor poked through it.
- **A cut can sever a part.** A feeder groove through both rails' supports, cut full depth, left a 200 mm ladder held
  together by a 1 mm bar. Grooves now keep a floor, and every part test asserts one solid after its cuts.
- **Features stack in ways the per-part tests miss.** Each tie plate was fine; each tab slot was fine; a tie sitting
  over a slot made its plate a bridge over air. Test the combination: the upper color rests on the lower one.

## Tests that can fail

- **Every test must be able to fail.** The clash test has a "too tight" variant that must report clashes. A cable
  modeled with `align=None` plus `.moved()` was shifted twice and made its own test vacuous.
- **Probe dimensions, don't trust construction.** Slice a thin box through the feature and measure the pieces
  (gauge between shoulders, hole diameter, groove width).
- **Tests derive from params**, so a one-line design change in `params.py` doesn't need test edits.

## Printing and slicers

- **The slicer is the final test.** Three bugs got past green unit tests and only showed in Bambu Studio: a plain
  3MF opened all on filament 1; a missing project config crashed the CLI; per-file mesh ids made three different
  ladders open as copies of one. Each now has a test that runs the file through Bambu Studio's CLI.
- **One color change per plate, on a layer boundary.** Two-color parts pooled onto their own plates; seams at 2.4 mm
  with 0.2 mm layers.
- **Print a fit coupon before anything else.** Clearances are a property of the printer + filament + profile.

## Working with the user

- **Match their screenshot to the model numerically.** A slicer screenshot showing "all three ladders have wire
  gaps" was right: counting posts (9 per ladder) showed three copies of the 203 mm middle ladder, which exposed the
  mesh-id bug. Counting ties in another screenshot resolved which way "one tie to the left" pointed.
- **Learn their vocabulary.** "Nubs" were the truss tabs; "the clip over the nubs" was a tie plate bridging a slot;
  "decks" were tie ladders. Repeat their word back with yours once, then use theirs.
- **Sketch options before building**, and let them kill ideas cheaply (a hold-down clip was dropped the moment they
  saw the tabs).
- **Ask for the reference file.** One project the user colored by hand in Bambu Studio showed the exact format, AMS
  slots and preset names, which turned guesswork into a template.

## Slicer truths the B-rep can't show (wire-rail curve, 2026-10-16)

- **Slice every plate, not just one, and read the G-code where it matters.**
  - A one-line (0.4 mm) lip passed every model test, and Bambu's classic walls left it out completely.
  - Arachne walls print sub-line features as fat beads that spill into seats and keep-outs.
  - Size printed features at two lines or more. Check the G-code's top layer and line positions against the
    keep-outs (G2/G3 arcs carry their centres in I/J).
- **Mesh tolerance is millimetres only if you ask for it.** build123d's `tessellate` is relative to edge size, so a
  long gentle arc was chorded 0.14 mm off. `cadkit.bambu3mf.mesh` now meshes with an absolute deflection.
- **A moved Compound's children don't move.** `Pos(...) * compound` moves the compound; `.children` keep their old
  place. Every two-color part on a packed plate was written at the same spot until `cadkit.plates.bodies()`
  applied the location. A roundtrip "same objects" check can't see it; only slicing a multi-part plate did.

## Tooling and process

- **Long suites run in the background.** Mark minutes-long tests slow, use pytest-xdist, iterate on `-m "not slow"`,
  run everything before each commit.
- **Viewer sends can vanish.** Open the OCP viewer page before sending; if the tab keeps the old model, reload and
  resend. A whole room is too big for one send; split it or use the web viewer.
- **Specs carry an amendment log.** Every change of mind gets a dated amendment with the why. Current-state docs
  (README, overview) are rewritten; history isn't.
- **Generated output stays out of git** (`out/`), and CLIs that litter their working directory run in a temp dir.
