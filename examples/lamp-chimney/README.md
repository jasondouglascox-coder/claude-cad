# Lamp chimney

<img src="docs/images/iso.png" width="49%" alt="the chimney"> <img src="docs/images/section.png" width="49%" alt="cut in half: the thick foot, the one-line wall">

A white printed replacement for the broken glass chimney of an LED oil-lamp-style lamp. The Ø40 foot drops into the
scalloped gallery, where the spring tabs grip it; above it the wall is a single 0.42 mm line, so it glows evenly
from the LED candle inside. A 45-degree shoulder with rounded bends steps down to the Ø26 neck; 131 mm tall.

- White PLA, AMS slot 1, printed upright with no supports: about 7.6 g and 1 h on the A1.
- The project carries its slicer settings: spiral (vase) mode, so there's no seam: the foot prints as solid layers,
  then one bead climbs the outside to the top. An 8 mm brim outside and inside the foot; peel both off before
  fitting, and trim the nib off the outside of the foot where the tabs grip.
- If the spiral fails, turn spiral mode off in Studio, set `wall = 0.84` (two lines) in `lamp_chimney/params.py`
  and rebuild.

```bash
uv sync
uv run pytest -n 4                    # print checks, sizes, the plate, and a Bambu slice (spiral, both brims)
uv run python -m lamp_chimney.build   # out/plates/lamp_chimney_1.3mf (File → Open Project), out/step, out/render
```

Design and decisions: `docs/specs/lamp-chimney.md`. Measurements: `docs/measurements.md`.
