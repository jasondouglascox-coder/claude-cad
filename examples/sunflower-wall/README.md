# Sunflower wall decor

A 400 mm (~16") sunflower for the wall, modeled on a real one: a big dark seed head (Fibonacci spiral) and two
rings of yellow petals that arch back. Bambu A1 + AMS lite, 0.20 mm Standard, PLA, no supports, no glue.

## What to print (`out/plates.csv`)

| Plate | Prints | Contents | Filament |
|---|---|---|---|
| `back_quarter.3mf` | 4 | back petal quarter + 2 snap pins | yellow (2) |
| `front_quarter.3mf` | 4 | front petal quarter | yellow (2) |
| `seed_head.3mf` | 1 | seed head | black (3), then brown (4): one color change |

AMS slots: 1 orange, 2 yellow, 3 black, 4 brown (`filaments` and `slot_*` in `sunflower/params.py`). The plates
open already colored: File → Open Project.

## Assembly

1. Lay the seed head face down on a towel.
2. Set the 4 front quarters (no keyhole) on it, hub to hub; their pin slots line up with the sockets.
3. Set the 4 back quarters on top, turned so their slots line up too (the seams land between petals).
4. Push a pin through each of the 8 slots, barbs first, until it clicks and its head sits flush.
5. Hang it on a pan-head screw (#8 / M4, head ≤ 8.5 mm × 3 mm) through the keyhole of whichever back quarter is
   at the top: head in the round hole, then let it drop.

## Commands

```bash
uv sync
uv run pytest -n 6 -m "not slow"          # ~2 min: printable, watertight, layers, fits, nothing overlaps
uv run pytest -n 5                        # + the plate files and Bambu Studio slicing each plate (~10 min)
uv run python -m sunflower.build          # out/plates, out/step, out/render
```

Design and decisions: `docs/specs/2026-10-15-sunflower-design.md`.
Before the first print, check `fit` (slot clearance) with `../fit-coupon`.
