# Loaf pan spacer

<img src="docs/images/front.png" width="60%" alt="Loaf pan spacer: the pan's cross-section with a pull tab and finger hole on top">

A thin sheet (0.6 mm, 3 layers) that stands across a loaf pan to split it while the dough rises. Pull it out by the
tab before baking: it's PLA. Its outline is the pan's inside cross-section, 0.3 mm in from each wall: 70 mm floor,
straight up 20 mm, out to 94 mm wide at 35 mm, straight up to the 60 mm rim, then 5 mm more, and a
40 × 30 mm tab with a 22 mm finger hole. Black, one piece, lies flat, no supports.
Sizes in `loaf_spacer/params.py`; design in `docs/specs/loaf-spacer.md`.

```bash
uv sync
uv run pytest -n 6                     # printable, sizes, the plate file, and a Bambu Studio slice (~10 s)
uv run python -m loaf_spacer.build     # out/plates/loaf_spacer_1.3mf (opens black), out/step, out/render
```

The picture in `docs/images/` is a copy of `out/render/front.png`; refresh it after a visible change.
