# Sheep antlers

<img src="docs/images/front.png" width="49%" alt="Reindeer antlers: two branching antlers rising from a curved band"> <img src="docs/images/iso.png" width="49%" alt="The antlers lying flat as printed, with the nub that goes into the sheep's slot">

Reindeer antlers for the little black sheep head: a flat 4 mm plate that sits against the back of the head, with a
5 mm wide nub, 5 mm long, that shoves into the arc-shaped slot there. The band behind the head is 8 mm tall, level
with the head top, so only the antlers show; they are 82 mm tip to tip and rise 45 mm over the head. Brown PETG (AMS slot 2), one piece, lies
flat, no supports. 

<img src="docs/images/fit_tabs.png" width="60%" alt="Five fit tabs, nubs 5.0 to 5.8 mm tall, numbered by notches">

Fit tabs first (`out/plates/fit_tabs_1.3mf`): nubs 5.0, 5.2, 5.4, 5.6, 5.8 mm tall, numbered 1–5 by the notches on
top. Shove each into the slot; put the one that holds in `nub_h`.

Sizes in `sheep_antlers/params.py`; design in `docs/specs/sheep-antlers.md`.

```bash
uv sync
uv run pytest -n 6                       # printable, sizes, the nub, the plate file, a Bambu Studio slice (~15 s)
uv run python -m sheep_antlers.build     # out/plates/sheep_antlers_1.3mf (opens brown PETG), out/step, out/render
```

The pictures in `docs/images/` are copies of `out/render/`; refresh them after a visible change.
