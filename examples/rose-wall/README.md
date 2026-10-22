# Rose wall decor

An open rose, about 8" (203 mm) across, to hang with the sunflower (`../sunflower-wall`). Printed in one go on a
Bambu A1 + AMS lite: red PLA, flat back on the bed, no assembly.

<img src="docs/images/front.png" width="49%" alt="rose, straight on"> <img src="docs/images/side.png" width="49%" alt="rose, three-quarter view">

24 outer petals on a golden-angle spiral rise, curve out and roll back down at their pointed tips; the centre is a
funnel of 8 small, tightly wrapped petals whose rims step down into the middle, like a real rose.

## Printing it

`uv run python -m rose_wall.build` writes `out/plates/rose.3mf`, a Bambu project that opens with everything set:
red PLA in AMS slot 1, PETG in slot 2. The outer petals' curl needs supports: tree supports, with PETG only where
they touch the rose (PETG doesn't stick to PLA, so they peel off clean). The centre needs none.
Sliced: 12.7 h, 304 g (289 g red, including the supports' bodies; 16 g PETG).

Hang it on a nail through the keyhole in the back: the nail goes where you want the rose's centre.

## Commands

```bash
uv sync
uv run pytest -m "not slow"          # one solid, size, the funnel, no supports in the centre, the keyhole, the plate
uv run pytest                        # + Bambu Studio slicing it with PETG-interface supports
uv run python -m rose_wall.build     # out/plates, out/rose.step, out/render
```

Design and decisions: `docs/specs/2026-10-22-rose-design.md`. The pictures in `docs/images/` are `out/render/`
copies; refresh them after a visible change.
