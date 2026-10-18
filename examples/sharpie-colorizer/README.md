# sharpie-colorizer

Made with claude-cad from the fit-coupon template: replace the coupon in `sharpie_colorizer/parts.py` with your part.

<img src="docs/images/iso.png" width="49%" alt="sharpie-colorizer">

```bash
uv sync
uv run pytest                     # print checks, dimensions, the plate file, the slicer (if installed)
uv run python -m sharpie_colorizer.build      # out/plates (open in your slicer), out/step, out/render
```

The pictures in `docs/images/` are copies of `out/render/`; refresh them after a visible change.
Decisions go in `docs/specs/` (with an Amendments section), real-world measurements in `docs/measurements.md`.
