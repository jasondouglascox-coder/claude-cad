"""uv run python -m sheep_antlers.build [--out out]: STEP for CAD, a Bambu Studio plate that opens in brown PETG,
and shaded previews in out/render/ (front.png: as the sheep wears them, seen from behind; iso.png)."""
import argparse
import sys
from pathlib import Path

from build123d import Color, Pos, export_step

from cadkit import bambu3mf
from cadkit.export import write_plates
from cadkit.plates import Plate, pack
from cadkit.render import render
from sheep_antlers.params import P
from sheep_antlers.parts import antlers, fit_tab


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sheep_antlers.build")
    ap.add_argument("--out", default="out")
    out = Path(ap.parse_args(argv).out)
    a = antlers(P)
    step = out / "step" / "sheep_antlers.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    export_step(a, step)
    tabs = [fit_tab(P, i) for i in range(len(P.fit_heights))]
    ams = bambu3mf.write_settings(out / "bambu_project_settings.config", list(P.filaments))
    plates = [Plate(f"sheep_antlers_{n + 1}", 1, items)
              for n, items in enumerate(pack([("sheep_antlers", a)], P.printer))]
    plates += [Plate(f"fit_tabs_{n + 1}", 1, items)
               for n, items in enumerate(pack([(t.label, t) for t in tabs], P.printer))]
    write_plates(plates, out / "plates", out / "plates.csv", lambda name: P.filament_brown, settings=ams)
    brown = Color(0.42, 0.27, 0.15)
    render([(a, brown)], out / "render" / "front.png", view=(0, 0, 1), px=600, crop=True)
    render([(a, brown)], out / "render" / "iso.png", view=(0.4, -0.7, 0.8), px=600, crop=True)
    row = [Pos(k * (P.tab_w + 4), 0, 0) * t for k, t in enumerate(tabs)]
    render([(t, brown) for t in row], out / "render" / "fit_tabs.png", view=(0.3, -0.8, 0.8), px=600, crop=True)
    print(f"wrote {out}/ (plates.csv lists what to print)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
