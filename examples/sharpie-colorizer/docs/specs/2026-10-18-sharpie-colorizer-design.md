# Sharpie colorizer

## Why

Buying a spool for every color is expensive, and for random prints the color only has to be close. This part lets
the user load **white filament on the A1's rear spool holder** and stain it with Sharpie markers on its way to the
head. One marker gives a light, streaky tint. Three of the same color give a deeper, more even color. Three
different colors would mix, but that's a side effect and not a goal.

## Goals

- Up to **three Sharpie Fine Point markers**, evenly spaced around the filament (120° apart), each tilted toward
  the filament with its felt tip pointing **downstream**, the direction the filament travels. Tilting the tips
  that way keeps the filament from catching on the felt. The user specifically wants the markers at an angle.
- **Press fit, no springs.** The user pushes a marker in until the felt touches and slightly presses into the
  filament path. As the felt wears, the user pushes it a little deeper. The socket grips the marker's narrow front
  section and must never bottom out on the wider body. That way the depth stays adjustable.
- Markers come out easily (a firm pull) to swap colors or cap them.
- **Loading** (new filament end pushed downstream) works with the markers in. **Unloading:** the user pulls the
  markers back a few mm first. The user confirmed this is fine. So the channel doesn't need a guide that steers a
  cut end, coming back upstream, past the tips.
- **Inline on the existing guide tube.** Today one 4 mm tube runs from the swivel fitting on the spool-holder arm
  down to the head. It becomes two tubes: swivel → colorizer, and colorizer → head. The spool holder and swivel
  stay untouched.
- **Clips onto the A1's top frame bar** (40 × 20 mm, rounded edges) beside the spool holder's own clamp. No
  screws. It can slide along the bar so it lines up with the tube's natural curve, and it doesn't flop around.
- Tube ends are **printed press-fit sockets** for the 4 mm guide tube.
- A **fit test print** first, like `examples/fit-coupon`: a few marker-socket sizes, a few tube-socket sizes, and
  a slice of the bar clip. The user picks the snug ones, and those go into `params.py` before the real part prints.

## Non-goals

- Color accuracy or matching.
- AMS use. This is only for the external spool and single-color prints.
- Keeping markers from drying out while they sit in the block. The user pulls and caps them.
- Springs, tip-wear compensation, or any moving parts.
- Keeping ink off the guide tube. Some smearing is fine because tube is cheap.

## Anti-goals (a failure even if it technically works)

- Enough drag or snagging that the A1 under-extrudes, or the filament jams at a felt tip or a socket edge. Light
  contact matters more than a deep color.
- Something that needs supports, or that only prints if it's babied.
- Markers that fall out in use.

## Constraints

- Printer: Bambu A1. Filament: 1.75 mm. Guide tube: 4 mm OD (the A1's stock tube).
- Frame bar: 40 mm wide × 20 mm tall, with rounded edges (corner radius not measured).
- Marker: Sharpie Fine Point, measured with a ruler. The numbers are in `docs/measurements.md`. Treat each as
  ±0.5 mm; the fit test settles the grip. In short: 12.5–13 mm body; an 11 mm front section that's straight for
  20 mm, then rounds in until 22.5 mm; a small plastic nose (~6 mm long, diameter not measured); then a felt bullet
  tip 5 mm long, 4 mm at the base. From the body shoulder to where the felt starts is ~32 mm, but the parts add up
  to ~28.5 mm, so the lengths are rough. The press fit lets the user set the depth by feel. The socket only has to
  grip the straight 20 mm and leave generous clearance for the curve, nose and tip to reach the filament without
  plastic touching plastic first.
- Repo print rules apply (`cadkit.checks`): flat on the bed, one solid per part, no supports, watertight, Z levels
  on layer multiples. One color, so no color changes.

## Decided by Claude (the user can overrule)

- Socket grip: on the straight 20 mm of the 11 mm front section, about 12–15 mm of engagement, so the 13 mm
  shoulder never seats even after the felt wears and the marker has been pushed deeper.
- Nose clearance: assume the nose is about 6 mm in diameter and leave at least 1 mm all round, since it wasn't
  measured.
- Fit test sizes: marker sockets around 10.6–11.6 mm in 0.2 steps, and tube sockets around 4.0–4.3 mm.
- Color: black (AMS slot 3), so ink stains don't show.
- Filament direction through the block: tube in at the top (from the swivel), tube out at the bottom (to the head).
- Mounting: the block sits **on top of the bar**. Nothing hangs below the bar's bottom face except the clip's thin
  lip, and that lip may wrap no further than the spool holder's own clamp already does. That keeps it clear of the
  X gantry at max Z. The filament axis runs roughly vertical or slightly sloped toward the head, and the outlet
  points the way the stock tube already curves down to the head.
- Project: `examples/sharpie-colorizer`, package `colorizer`, built from the `fit-coupon` template with the
  usual tests, spec and README renders. The ruler measurements go in `docs/measurements.md`.

## Left to the builder

- Marker tilt angle (somewhere in the 30–45° range from the filament axis looks right), and block shape and length.
- Whether the clip and the block are one printed part or two (two is fine if that's what printing without supports
  needs), and print orientation.
- How the filament channel opens where the tips meet it (a window or pocket, so the felt reaches the filament and
  ink doesn't build up on a sharp edge), and channel diameter.
- Clip geometry (snap-over C-clip or slide-on), with enough grip that the block doesn't rotate when a marker gets
  pushed in.
- Where along the bar it sits relative to the spool-holder clamp.

## Amendments

- **2026-10-18: builder's choices while implementing** (the plan is in `docs/plans/2026-10-18-sharpie-colorizer.md`).
  - The package is `sharpie_colorizer` (what `cadkit.new` names it), not `colorizer`.
  - **Two parts.** The clip prints lying on its profile, so the snap flexes along the layers. The block prints
    upright. They join by a dovetail rail on the clip, with a 45° peaked slot roof in the block so nothing bridges.
  - **The channel sits 25.6 mm in front of the bar's center**, so the outlet tube drops past the clip's front wall.
    The block cantilevers off the bar's top. Nothing but the clip lips goes below the bar.
  - **Tilt is 42°**, the top end of the range, so the 1 mm nose clearance stays out of the channel's far half.
  - **The felts are staggered 8 mm along a continuous Ø2.4 channel** at azimuths 270° (back), 30° and 150°. The
    wall opposite each felt is unbroken, which guides a loading end past it. The window is the felt cone shifted
    1 mm deeper, so a worn felt pushed back in still clears plastic.
  - **The mouth is 29 mm from the felt point.** That gives 12 mm of grip at the 32 mm reading, and a ≥3 mm
    shoulder gap at the 28.5 mm reading even after 1 mm of wear (`wear_max`).
  - **The clip hook is fit-tested** at 1.5 / 2.0 / 2.5 mm. The default of 2.0 strains the wall about 1.4% while
    snapping on.
- **2026-10-18: final review fixes.**
  - **The block locks onto the rail with a filament pin.** A ~14 mm stub of the 1.75 mm filament goes down a
    Ø2 hole in the block's base into a teardrop hole in the rail. Without it, pushing a marker in (58% of the force
    runs along the bar) could slide the block off the rail. It's not a screw: there's no hardware, and it pulls
    out with fingers.
  - **The inlet is raised** so 0.8 mm of plastic separates its funnel from the top marker's nose bore. The column
    is now 52.6 mm tall.
  - **The slot is chamfered 0.4 mm where it meets the bed**, so elephant foot can't bind the rail.
- **2026-10-18: fit-test results.**
  - Marker socket is 10.7, between the almost-too-tight 10.6 and the smooth-sliding 10.8. The marker's front
    section is modelled at 10.7 too.
  - Clip hook stays 2.0 (slice 2).
  - The bar's height is 19.4, not 20. Slice 2 had at least 1 mm of vertical play.
  - Details are in `docs/measurements.md`.
  - Tube sockets are 4.2: tight. 4.3 pulled out easily.
