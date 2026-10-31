# Cat decals

<img src="docs/images/poses.png" width="60%" alt="twelve cat silhouettes: sitting, from behind, lying, playing with yarn, stretching, arched, asleep, walking, washing, pouncing, reaching, peeking"> <img src="docs/images/sheet.png" width="36%" alt="one of each cat across the top of a 24 by 24 inch mat">

Little black cats cut from vinyl on a Silhouette Cameo. These are not 3D prints: each cat is one solid silhouette,
and the blade cuts only its outline. Twelve poses: sitting, from behind, lying, batting a ball of yarn, stretching,
arched (the Halloween one), asleep, walking, washing a paw, pouncing, reaching up, and peeking over an edge. The sheet
has one of each, 3" on its longer side and ½" apart, across the top of the 24" × 24" mat: duplicate and scale them in
Studio.

Every pose has to read from its outline alone, so ears, tails and legs do the work, and the tests hold every cut to
what weeds cleanly: no leg, tail or ear narrower than ⅛", and no hole (between legs, in the yarn's winding) narrower
than 0.1".

## Cutting

1. Silhouette Studio (Basic Edition is enough): **File → Open** `out/cat_sheet_in.dxf`.
2. Measure the square at the left. DXF files carry no units, so Studio guesses: if it isn't 1", scale everything
   together until it is.
3. Duplicate and resize the cats you want, set the page and mat to 24 × 24, and cut with your usual vinyl setting.

```bash
uv sync
uv run pytest -n 4                # weedable cuts, sizes, the sheet on the mat, DXFs read back to scale
uv run python -m cat_decals.build # out/cat_sheet_in.dxf, out/render/*.png
```

The size and spacing live in `cat_decals/params.py`, and the poses in `cat_decals/cats.py`. Decisions are recorded in
`docs/specs/cat-decals.md`.
