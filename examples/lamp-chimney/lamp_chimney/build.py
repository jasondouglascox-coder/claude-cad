"""uv run python -m lamp_chimney.build [--out out]: STEP for CAD, a Bambu Studio plate that opens white, in spiral
(vase) mode with brims inside and outside the foot, and shaded previews in out/render (iso.png, section.png: cut in half)
to copy to docs/images/ after a visible change."""
import argparse
import sys
from pathlib import Path

from build123d import Align, Box, Color, Pos, export_step

from cadkit import bambu3mf
from cadkit.export import write_plates
from cadkit.plates import Plate
from cadkit.render import render
from lamp_chimney.params import P
from lamp_chimney.parts import center, chimney, on_bed

# vase mode: the foot as solid layers, then one bead climbing the outside to the top, so no seam (and none of the
# floating-region warning Studio gives a one-line wall printed layer by layer); the brim holds the narrow foot down
# on both sides. Studio's GUI wants one wall loop, no top shell and no sparse infill with spiral mode, or it asks to
# change them on opening; the foot is all bottom shell, so it stays solid
SLICER = {"spiral_mode": "1", "bottom_shell_layers": str(P.foot_layers), "wall_loops": "1", "top_shell_layers": "0",
          "sparse_infill_density": "0%", "brim_type": "outer_and_inner", "brim_width": str(P.brim)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lamp_chimney.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    c = chimney(P)
    step = out / "step" / "lamp_chimney.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    export_step(c, step)
    settings = bambu3mf.write_settings(out / "bambu_project_settings.config", [("PLA", "#FFFFFF")] * 4,
                                       overrides=SLICER)
    write_plates([Plate("lamp_chimney_1", 1, [("lamp_chimney", on_bed(P))])], out / "plates",
                 out / "plates.csv", lambda name: P.filament_white, settings=settings)
    white = Color(0.93, 0.93, 0.91)
    half = c & Pos(0, center(P)[1], 0) * Box(4 * P.foot_d, 4 * P.foot_d, 2 * P.height, align=(Align.MIN,) * 3)
    render([(c, white)], out / "render" / "iso.png", view=(0.5, -1, 0.35), px=700)
    render([(half, white)], out / "render" / "section.png", view=(0, -1, 0.1), px=700)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
