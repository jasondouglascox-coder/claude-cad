# Room measurements (laser measure + stud finder)

All in inches. Stud positions are stud centers at track height (~9 ft, above the door headers).

## Right wall (front to back), 2026-10-13
- Total length: **170"** (confirmed 2026-10-14; the model used 168" until then).
- Double French door: **2"–65" from the back wall**, measured to the outside of the trim, so the framing sits slightly inside that.
- Stud centers, from the back wall: **55.75, 64.5, 79.75, 104, 127.25, 151.5**.
  The last two were measured from the front wall as 42.75 and 18.5.
- Gaps: 8.75, 15.25, 24.25, 23.25, 24.25, then 18.5 to the front wall.
  - The 8.75" gap falls mostly on the bridge-corner curve.
  - The three ~24" gaps are longer than the 18.9" max bay (each half bay must fit the bed). Decide later: a mid-gap
    bracket on drywall toggles, or a 3-piece bay.

## Front wall (right wall to left wall), 2026-10-13
- Exterior wall. The electronic stud finder is unreliable here, so use a magnetic one.
- Total length: **126.125"** by laser (126.25" from 30.5 + 65 + 30.75, which matches within 1/8").
  Re-measured 2026-10-14 as **125.875"**, three times. See "Whole room" below.
- Window trim: **30.5"–95.5" from the right wall**.
- Stud centers from the right wall: **18, 52.5, 108.25** (measured, at track height). 108.25 was measured as 17 7/8 from the left wall;
  it mirrors the 18" stud at the right end.
- Estimated: the window's side studs are at **~31.0 and ~95.0**, 0.5" inside the trim, as at the French door (trim 65, stud 64.5).
- Header over the window: a 2x8, 2x10 or 2x12 pair sitting on the window framing at ~84". Bracket screws land at
  ~93" and ~95" (rail top 96" = 12" below the 108" ceiling; brackets hang ~3.25").
  - A 2x12 (to ~95") means a bracket can go anywhere from ~31 to ~95.
  - A 2x8 or 2x10 means the brackets must hit the cripple studs above it.
  - To do: probe with a finish nail at 93" and 95" at 2–3 spots across the window.
- So far, from the right wall: 18 | ~31 (est.) | 52.5 | ~95 (est.) | 108.25 | left wall at 126.125.
  The open question is ~52.5 to ~95 over the window (header check).
- The loop closes along this wall (wall-mounted; the wall itself stays out of the render).

## Whole room, 2026-10-14
Model names below. That day the user stood the other way round and called the long wall "left" and this
list's left wall "right".
- Right wall (long, French doors): **170"**.
- Alcove: **43.75" × 43.75"**.
- Back wall, left wall to the bump-out corner: **82.5"** (the model had 83"). The user is sure of it.
- Left wall: **126.375"**.
- Front wall: **125.875"**, the same on three readings.

Closure:
- Front to back: left 126.375 + alcove 43.75 = 170.125 against the right wall's 170. That's 1/8", within a tape reading.
- Across: back 82.5 + alcove 43.75 = 126.25 against the front wall's 125.875. The room is **3/8" narrower at the
  front**. Three matching readings say the room isn't square; the reading is fine.

How it's handled:
- `room.Room` stays square on the right wall, alcove and back wall, so its front and left walls are both 126.25".
- `Room.misfit()` keeps the measured front and left walls. `build room`, `web`, `glb` and `show room` print a note
  when either is more than 1/8" off.
- On the real loop the straight runs absorb the difference. The corners are identical, and each run's bays come from
  its real bracket positions, so the front run just comes out 3/8" shorter.
  - Across a side wall that's about 0.17°, nothing at a rail joint.
  - The bridge corner's bump-out anchor also lets its rods slide ±9.5 mm.
